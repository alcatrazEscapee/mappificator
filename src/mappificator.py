# This is why we can't have nice things

import argparse
from collections import defaultdict
from typing import Dict, Tuple, List, Set, Mapping, Optional

from providers import fabricmc, parchmentmc, architectury
from providers.parchmentmc import MethodInheritanceTree
from util import utils
from util.mappings import Mappings


def main():
    """ Entry point """

    parser = argparse.ArgumentParser(description='A collection of bodging scripts to work with Minecraft mappings and alleviate suffering.')

    parser.add_argument('--version', type=str, default=None, help='Sets the version of the exported mappings.')
    parser.add_argument('--skip-publish', action='store_true', dest='skip_publish', default=False, help='Skips publishing and only writes the export locally to ./build/')

    # Individual versions
    parser.add_argument('--mc-version', type=str, default='1.17', help='The Minecraft version')
    parser.add_argument('--parchment-version', type=str, default='2021.07.09-nightly-SNAPSHOT', help='The parchment mappings version')
    parser.add_argument('--yarn-version', type=str, default='9', help='The fabric yarn mappings version')
    parser.add_argument('--crane-version', type=str, default='14', help='The architectury crane mappings version')

    args = parser.parse_args()
    version = args.version
    if version is None:
        version = 'mappificator-%s-y%s' % (args.parchment_version.split('-')[0], args.yarn_version)

    print('Loading blackstone')
    obf_to_moj, method_inheritance = parchmentmc.read_blackstone(args.mc_version)

    print('Loading parchment')
    parchment = parchmentmc.read_parchment(args.mc_version, args.parchment_version)

    print('Loading crane')
    crane = architectury.read_crane(args.mc_version, args.crane_version)

    print('Loading intermediary')
    intermediary = fabricmc.read_intermediary(args.mc_version)

    print('Loading yarn')
    yarn = fabricmc.read_yarn(args.mc_version, args.yarn_version)

    print('Remapping yarn onto mojmap')
    moj_to_yarn = remap_yarn_onto_mojmap(obf_to_moj, method_inheritance, intermediary, yarn)

    print('Creating merged mappings')

    merged = obf_to_moj.remap()
    create_merged_mappings(merged, parchment, crane, moj_to_yarn)

    print('Writing merged mappings')
    parchmentmc.write_parchment(merged, args.mc_version, version)

    if not args.skip_publish:
        print('Publishing to maven local')
        parchmentmc.publish_parchment(args.mc_version, version)


def remap_yarn_onto_mojmap(obf_to_moj: Mappings, method_inheritance: MethodInheritanceTree, intermediary: Mappings, yarn: Mappings) -> Mappings:
    # First - fix issues with intermediary
    # intermediary does not include inherited methods - use the method inheritance tree to fill them out (mostly)
    for method in obf_to_moj.methods.keys():
        if method not in intermediary.methods and method in method_inheritance:
            obf_class, obf_method, obf_desc = method
            for override_obf_class in method_inheritance[method]:
                key = override_obf_class, obf_method, obf_desc
                if key in intermediary.methods:
                    new_method = intermediary.add_method(intermediary.add_class(obf_class), obf_method, obf_desc)
                    new_method.mapped = intermediary.methods[key].mapped
                    break

    # Inherit mojmap (un-obf) mappings, and then compose obf -> moj -> intermediary (inherited moj) -> yarn
    intermediary.inherit_domain(obf_to_moj)
    return obf_to_moj.invert().compose(intermediary).compose(yarn)


def create_merged_mappings(named: Mappings, *sources: Mappings):
    # Copy package level docs from parchment
    for key, named_package in named.packages.items():
        for source in sources:
            if key in source.packages:
                named_package.docs += source.packages[key].docs

    add_merged_docs(named.classes, *map(lambda p: p.classes, sources))
    add_merged_docs(named.fields, *map(lambda p: p.fields, sources))
    add_merged_docs(named.methods, *map(lambda p: p.methods, sources))
    add_merged_params(named, *sources)


def add_merged_docs(named: Mapping, *sources: Mapping):
    for key, named_obj in named.items():
        for source in sources:
            if key in source:
                obj = source[key]
                if named_obj.docs:  # Add a space if this isn't the first entry
                    named_obj.docs.append('')
                named_obj.docs += obj.docs


def add_merged_params(named: Mappings, *sources: Mappings):
    use_enhanced_lambda_conflict_avoidance = False
    illegal_names = generate_reserved_class_names(named) | utils.JAVA_KEYWORDS

    # The default classes is a map of name -> class
    # We need to index it into a map of name -> (class, any inner classes, any anonymous classes)
    # Both of these are inferred by the class name
    indexed_classes: Dict[str, Tuple[List[str], List[str]]] = defaultdict(lambda: ([], []))  # inner. anon
    for class_name, named_class in named.classes.items():
        if '$' in class_name:  # Inner or Anonymous classes
            root_class, *_, target_class = class_name.split('$')
            indexed_classes[root_class][1 if target_class.isnumeric() else 0].append(class_name)
        else:  # Include classes that may not have inner or anonymous classes
            _ = indexed_classes[class_name]

    names = ['parchment', 'crane', 'yarn', 'automatic']
    param_name_stats = [0] * (len(sources) + 1)

    # Iterate through indexed classes (top level class source files)
    for class_name, index in indexed_classes.items():
        inner_class_names, anon_class_names = index

        # We need to group methods by their conflict resolution state - essentially, group methods that may conflict with other methods
        # The top level is normal class and inner class methods. These are assigned names first, and none can conflict with each other
        # Each top level method is added to a 'reserved group' just based on the method name, not descriptor
        # Lambda methods are next: By inspecting the obf. name, we can infer the source method by name. These parameters are then named against those reserved names
        # Methods belonging to anonymous classes are named last, and may conflict with any existing parameter as the location of the anonymous class it not known.
        class_methods: List[Mappings.Method] = []
        lambda_methods: List[Mappings.Method] = []
        unique_methods: List[Mappings.Method] = []

        if not use_enhanced_lambda_conflict_avoidance:
            class_methods += lambda_methods
            lambda_methods = []

        # Group all methods into lists of unique and class level conflicts
        add_methods_by_conflict_status(named.classes[class_name], lambda_methods, unique_methods)
        for inner_class_name in inner_class_names:
            add_methods_by_conflict_status(named.classes[inner_class_name], lambda_methods, unique_methods)
        for anon_class_name in anon_class_names:  # Anonymous classes are all class-level conflicts
            add_methods_by_conflict_status(named.classes[anon_class_name], class_methods, class_methods)

        reserved_names_by_method: Dict[str, Set[str]] = defaultdict(set)  # reserved names for each method, after it has been assigned
        class_reserved_names: Set[str] = set()

        # Apply parameter names to all methods, including copying docs and generating any missing parameters procedurally
        for named_method in sorted(unique_methods, key=lambda k: (k.name, k.desc)):
            reserved_names: Set[str] = set()
            for named_param in named_method.parameters.values():
                param_key = (class_name, named_method.name, named_method.desc, named_param.index)
                mapped_name, i = generate_param_name_from_sources(param_key, named_param, sources, illegal_names, reserved_names)
                reserved_names.add(mapped_name)
                class_reserved_names.add(mapped_name)
                param_name_stats[i] += 1
            reserved_names_by_method[named_method.name] |= reserved_names

        # Apply parameter names to lambda methods, only conflicting with possible owning methods
        for named_method in sorted(lambda_methods, key=lambda k: (k.name, k.desc)):
            reserved_names = reserved_names_by_method[named_method.name]
            for named_param in named_method.parameters.values():
                param_key = (class_name, named_method.name, named_method.desc, named_param.index)
                mapped_name, i = generate_param_name_from_sources(param_key, named_param, sources, illegal_names, reserved_names)
                class_reserved_names.add(mapped_name)
                param_name_stats[i] += 1

        # Apply parameter names to lambda and anonymous class methods, using the class reserved names to avoid conflicts
        for named_method in sorted(class_methods, key=lambda k: (k.name, k.desc)):
            for named_param in named_method.parameters.values():
                param_key = (class_name, named_method.name, named_method.desc, named_param.index)
                mapped_name, i = generate_param_name_from_sources(param_key, named_param, sources, illegal_names, class_reserved_names)
                class_reserved_names.add(mapped_name)
                param_name_stats[i] += 1

    print('Parameters sourced from:')
    for k, v in zip(names, param_name_stats):
        print('  %s = %d' % (k, v))


def generate_reserved_class_names(named: Mappings) -> Set[str]:
    classes = set()
    for named_class in named.classes.keys():
        if '/' in named_class:  # Remove packages
            named_class = named_class[named_class.rindex('/') + 1:]
        if '$' in named_class:  # Ignore inner classes for this rule, as in providers they use '$' in the name
            continue
        named_class = named_class.lower()  # lowercase the entire class name
        classes.add(named_class)
    return classes


def add_methods_by_conflict_status(named_class: Mappings.Class, lambda_methods: Optional[List[Mappings.Method]], simple_methods: Optional[List[Mappings.Method]]):
    for method_key, named_method in named_class.methods.items():
        if named_method.is_lambda:
            lambda_methods.append(named_method)
        else:
            simple_methods.append(named_method)


def generate_param_name_from_sources(param_key: Tuple[str, str, str, int], named_param: Mappings.Parameter, sources: Tuple[Mappings], illegal_names: Set[str], reserved_names: Set[str]) -> Tuple[str, int]:
    mapped_name = None

    # Apply mappings and docs from providers
    mapped_source = -1
    for i, source in enumerate(sources):
        if param_key in source.parameters:
            source_param = source.parameters[param_key]
            if mapped_name is None and source_param.mapped is not None:
                mapped_name = source_param.mapped
                mapped_source = i
            if source_param.docs:
                if named_param.docs:
                    named_param.docs.append('')
                named_param.docs += source_param.docs

    if mapped_name in illegal_names:
        # Mark this as an automatic name to avoid conflicts
        mapped_name += '_'

    # Apply default naming
    if mapped_name is None:
        mapped_name = generate_param_name(named_param.desc)

    mapped_name = resolve_name_conflicts(mapped_name, reserved_names)
    named_param.mapped = mapped_name
    return mapped_name, mapped_source


def generate_param_name(param_type: str) -> str:
    name, arrays = utils.convert_descriptor_to_type(param_type)
    if '/' in name:  # Remove packages
        name = name.split('/')[-1]
    if '$' in name:  # Remove inner classes
        name = name.split('$')[-1]
    if arrays > 0:  # Add 'Array' for array levels
        name += 'Array'
    name = name[0].lower() + name[1:]  # lowerCamelCase
    name += '_'  # Signal that this is an automatic name, prevent conflicts with local variables
    return name


def resolve_name_conflicts(name: str, reserved_names: Set[str]) -> str:
    if name in reserved_names:
        auto = name.endswith('_')
        proto_name = name[:-1] if auto else name
        proto_name = proto_name.rstrip('0123456789')  # strip any previous numeric value off the end
        count = 1
        while name in reserved_names:
            name = proto_name + str(count)
            count += 1
            if auto:
                name += '_'
    return name


if __name__ == '__main__':
    main()
