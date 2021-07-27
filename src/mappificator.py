# This is why we can't have nice things

from argparse import ArgumentParser
from collections import defaultdict
from typing import Dict, Tuple, List, Set, Mapping, Optional

from providers import fabricmc, parchmentmc, architectury
from providers.parchmentmc import MethodInheritanceTree
from util import utils
from util.mappings import Mappings


def main():
    """ Entry point """

    parser = ArgumentParser(description='A collection of bodging scripts to work with Minecraft mappings and alleviate suffering.')

    parser.add_argument('-v', '--version', type=str, default=None, help='Sets the version of the exported mappings.')
    parser.add_argument('-p', '--publish', action='store_true', dest='publish', default=False, help='Publish the export to the user\'s maven local')

    # Options
    parser.add_argument('--providers', nargs='+', choices=('parchment', 'crane', 'yarn'), default=('parchment', 'crane', 'yarn'), help='Providers to source mappings from.')
    parser.add_argument('--improved-lambda-conflict-avoidance', action='store_true', dest='improved_lambda_conflict_avoidance', default=False, help='Enables an enhanced method for avoiding lambda parameter conflicts, by grouping lambda parameters local to their owning method(s) as determined by the official name of the lambda in source.')
    parser.add_argument('--yarn-mapping-comments', action='store_true', default=False, dest='yarn_mapping_comments', help='Enables adding javadoc comments to classes, fields, and methods with their corresponding yarn name, if present.')
    parser.add_argument('--pretty-print-merged-mappings', action='store_true', dest='pretty_print_merged_mappings', help='Pretty prints (with indents and newlines) a raw JSON of the merged mappings in addition to the compressed format.')

    # Individual versions
    parser.add_argument('--mc-version', type=str, default='1.17', help='The Minecraft version')
    parser.add_argument('--parchment-version', type=str, default='2021.07.21', help='The parchment mappings version')
    parser.add_argument('--yarn-version', type=str, default='9', help='The fabric yarn mappings version')
    parser.add_argument('--crane-version', type=str, default='14', help='The architectury crane mappings version')

    args = parser.parse_args()
    version = args.version
    if version is None:
        version = 'mappificator'
        if 'parchment' in args.providers:
            version += '-p%s' % args.parchment_version.split('-')[0]
        if 'crane' in args.providers:
            version += '-c%s' % args.crane_version
        if 'yarn' in args.providers:
            version += '-y%s' % args.yarn_version

    sources = []

    print('Loading blackstone')
    obf_to_moj, method_inheritance = parchmentmc.read_blackstone(args.mc_version)

    if 'parchment' in args.providers:
        print('Loading parchment')
        parchment = parchmentmc.read_parchment(args.mc_version, args.parchment_version)
        sources.append(parchment)

    if 'crane' in args.providers:
        print('Loading crane')
        crane = architectury.read_crane(args.mc_version, args.crane_version)
        sources.append(crane)

    if 'yarn' in args.providers:
        print('Loading intermediary and yarn')
        intermediary = fabricmc.read_intermediary(args.mc_version)
        yarn = fabricmc.read_yarn(args.mc_version, args.yarn_version)
        moj_to_yarn = remap_yarn_onto_mojmap(obf_to_moj, method_inheritance, intermediary, yarn)
        if args.yarn_mapping_comments:
            append_mapping_javadoc(moj_to_yarn, 'Yarn: ')
        sources.append(moj_to_yarn)

    print('Creating merged mappings')
    merged = obf_to_moj.remap()
    create_merged_mappings(merged, *sources, improved_lambda_conflict_avoidance=args.improved_lambda_conflict_avoidance)

    print('Writing merged mappings')
    parchmentmc.write_parchment(merged, args.mc_version, version, args.pretty_print_merged_mappings)

    if args.publish:
        print('Publishing to maven local')
        parchmentmc.publish_parchment(args.mc_version, version)

        print('Published to channel: \'parchment\' version: \'%s-%s\'' % (version, args.mc_version))


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


def append_mapping_javadoc(mappings: Mappings, prefix: str):
    def apply(obj: Dict):
        for mapped in obj.values():
            if mapped.mapped:
                if mapped.docs:
                    mapped.docs.append('')
                mapped.docs.append(prefix + mapped.mapped)

    apply(mappings.classes)
    apply(mappings.fields)
    apply(dict((k, v) for k, v in mappings.methods.items() if v.mapped != '<init>' and not v.is_lambda))  # exclude constructors and lambda methods


def create_merged_mappings(named: Mappings, *sources: Mappings, improved_lambda_conflict_avoidance: bool = False):
    # Copy package level docs from parchment
    for key, named_package in named.packages.items():
        for source in sources:
            if key in source.packages:
                named_package.docs += source.packages[key].docs

    add_merged_docs(named.classes, *map(lambda p: p.classes, sources))
    add_merged_docs(named.fields, *map(lambda p: p.fields, sources))
    add_merged_docs(named.methods, *map(lambda p: p.methods, sources))
    add_merged_params(named, *sources, improved_lambda_conflict_avoidance=improved_lambda_conflict_avoidance)


def add_merged_docs(named: Mapping, *sources: Mapping):
    for key, named_obj in named.items():
        for source in sources:
            if key in source:
                obj = source[key]
                if named_obj.docs:  # Add a space if this isn't the first entry
                    named_obj.docs.append('')
                named_obj.docs += obj.docs


def add_merged_params(named: Mappings, *sources: Mappings, improved_lambda_conflict_avoidance: bool = False):
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

    # Iterate through indexed classes (top level class source files)
    for class_name_key, index in indexed_classes.items():
        inner_class_names, anon_class_names = index

        # We need to group methods by their conflict resolution state - essentially, group methods that may conflict with other methods
        # The top level is normal class and inner class methods. These are assigned names first, and none can conflict with each other
        # Each top level method is added to a 'reserved group' just based on the method name, not descriptor
        # Lambda methods are next: By inspecting the obf. name, we can infer the source method by name. These parameters are then named against those reserved names
        # Methods belonging to anonymous classes are named last, and may conflict with any existing parameter as the location of the anonymous class it not known.
        # Methods are also grouped with their owning class, as the class_name_key is only the root class (not including anonymous or inner classes) and as such, is necessary to extract mappings from external sources for those methods.
        class_methods: List[Tuple[str, Mappings.Method]] = []
        lambda_methods: List[Tuple[str, Mappings.Method]] = []
        unique_methods: List[Tuple[str, Mappings.Method]] = []

        # Group all methods into lists of unique and class level conflicts
        add_methods_by_conflict_status(named.classes[class_name_key], lambda_methods, unique_methods)
        for inner_class_name in inner_class_names:
            add_methods_by_conflict_status(named.classes[inner_class_name], lambda_methods, unique_methods)
        for anon_class_name in anon_class_names:  # Anonymous classes are all class-level conflicts
            add_methods_by_conflict_status(named.classes[anon_class_name], class_methods, class_methods)

        if not improved_lambda_conflict_avoidance:
            class_methods += lambda_methods
            lambda_methods = []

        reserved_names_by_method: Dict[str, Set[str]] = defaultdict(set)  # reserved names for each method, after it has been assigned
        class_reserved_names: Set[str] = set()

        # Apply parameter names to all methods, including copying docs and generating any missing parameters procedurally
        for class_name, named_method in sorted(unique_methods, key=index_sort):
            reserved_names: Set[str] = set()
            for named_param in named_method.parameters.values():
                param_key = (class_name, named_method.name, named_method.desc, named_param.index)
                mapped_name = generate_param_name_from_sources(param_key, named_param, sources, reserved_names)
                reserved_names.add(mapped_name)
                class_reserved_names.add(mapped_name)
            reserved_names_by_method[named_method.name] |= reserved_names

        # Apply parameter names to lambda methods, only conflicting with possible owning methods
        for class_name, named_method in sorted(lambda_methods, key=index_sort):
            reserved_names = reserved_names_by_method[named_method.name]
            for named_param in named_method.parameters.values():
                param_key = (class_name, named_method.name, named_method.desc, named_param.index)
                mapped_name = generate_param_name_from_sources(param_key, named_param, sources, reserved_names)
                class_reserved_names.add(mapped_name)

        # Apply parameter names to lambda and anonymous class methods, using the class reserved names to avoid conflicts
        for class_name, named_method in sorted(class_methods, key=index_sort):
            for named_param in named_method.parameters.values():
                param_key = (class_name, named_method.name, named_method.desc, named_param.index)
                mapped_name = generate_param_name_from_sources(param_key, named_param, sources, class_reserved_names)
                class_reserved_names.add(mapped_name)


def add_methods_by_conflict_status(named_class: Mappings.Class, lambda_methods: Optional[List[Tuple[str, Mappings.Method]]], simple_methods: Optional[List[Tuple[str, Mappings.Method]]]):
    for method_key, named_method in named_class.methods.items():
        if named_method.is_lambda:
            lambda_methods.append((named_class.name, named_method))
        else:
            simple_methods.append((named_class.name, named_method))


def generate_param_name_from_sources(param_key: Tuple[str, str, str, int], named_param: Mappings.Parameter, sources: Tuple[Mappings], reserved_names: Set[str]) -> str:
    mapped_name = None

    # Apply mappings and docs from providers
    for i, source in enumerate(sources):
        if param_key in source.parameters:
            source_param = source.parameters[param_key]
            if mapped_name is None and source_param.mapped is not None:
                mapped_name = source_param.mapped
            if source_param.docs:
                if named_param.docs:
                    named_param.docs.append('')
                named_param.docs += source_param.docs

    if mapped_name is None:  # generate a default name
        mapped_name = generate_param_name(named_param.desc)

    mapped_name += '_'  # conflict resolution with fields and/or local variables
    mapped_name = resolve_name_conflicts(mapped_name, reserved_names)

    named_param.mapped = mapped_name
    return mapped_name


def generate_param_name(param_type: str) -> str:
    name, arrays = utils.convert_descriptor_to_type(param_type)
    if '/' in name:  # Remove packages
        name = name.split('/')[-1]
    if '$' in name:  # Remove inner classes
        name = name.split('$')[-1]
    if arrays > 0:  # Add 'Array' for array levels
        name += 'Array'
    name = name[0].lower() + name[1:]  # lowerCamelCase
    name = name.rstrip('0123456789')  # strip numeric values off the end by default
    return name


def resolve_name_conflicts(name: str, reserved_names: Set[str]) -> str:
    if name in reserved_names:
        proto_name = name[:-1].rstrip('0123456789')  # strip any previous numeric value off the end
        count = 1
        while name in reserved_names:
            name = proto_name + str(count) + '_'
            count += 1
    return name


def index_sort(key: Tuple[str, Mappings.Method]) -> Tuple[str, ...]:
    return key[0], key[1].name, key[1].desc


if __name__ == '__main__':
    main()
