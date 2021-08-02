# ParchmentMC
# Produces Parchment (mappings) and Blackstone (metadata)
# https://github.com/ParchmentMC/

import json
import os
import subprocess
import zipfile
from typing import Dict, Tuple, Any, Set

from util import mapping_downloader, utils
from util.mappings import Mappings

MethodInheritanceTree = Dict[Tuple[str, str, str], Set[str]]  # (obf class, obf method, obf desc) -> { overriding obf classes }


def read_parchment(mc_version: str, parchment_version: str) -> Mappings:
    parchment = mapping_downloader.load_parchment(mc_version, parchment_version)
    named = Mappings()
    parse_parchment(parchment, named)
    return named


def write_parchment(data: Mappings, mc_version: str, version: str, write_plain: bool = False):
    """
    Writes a parchment mappings object to a parchment formatted JSON file
    The source set is assumed to be mojmap, with named parameters and javadocs
    """
    # Write directly to a zip file
    file_path = os.path.join(mapping_downloader.CACHE_PATH, 'parchment-%s-%s-checked.zip' % (mc_version, version))
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    json_data = utils.filter_none({
        'version': '1.0.0',
        'packages': [{
            'name': p.name,
            'javadoc': p.docs
        } for p in data.packages.values() if p.docs is not None],
        'classes': [{
            'name': c.name,
            'javadoc': c.docs if c.docs else None,
            'fields': [{
                'name': f.name,
                'descriptor': f.desc,
                'javadoc': f.docs
            } for f in c.fields.values() if f.docs],
            'methods': [{
                'name': m.name,
                'descriptor': m.desc,
                'javadoc': m.docs if m.docs else None,
                'parameters': [{
                    'index': p.index,
                    'name': p.mapped,
                    'javadoc': '\n'.join(p.docs) if p.docs else None
                } for p in m.parameters.values() if p.mapped or p.docs]
            } for m in c.methods.values() if m.docs or any(p.mapped or p.docs for p in m.parameters.values())]
        } for c in data.classes.values()]
    })

    with zipfile.ZipFile(file_path, 'w') as f:
        f.writestr('parchment.json', json.dumps(json_data))

    if write_plain:
        plain_path = os.path.join(mapping_downloader.CACHE_PATH, 'parchment-%s-%s-checked.json' % (mc_version, version))
        mapping_downloader.save_text(plain_path, json.dumps(json_data, indent=2))


def publish_parchment(mc_version: str, version: str):
    file_path = os.path.join(mapping_downloader.CACHE_PATH, 'parchment-%s-%s-checked.zip' % (mc_version, version))
    if not os.path.isfile(file_path):
        raise ValueError('Must first build export before publishing to maven local')

    print('Publishing export to maven local...')
    proc = subprocess.Popen('mvn install:install-file -Dfile=%s -DgroupId=org.parchmentmc.data -DartifactId=parchment-%s -Dversion=%s -Dpackaging=zip -Dclassifier=checked' % (file_path, mc_version, version), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    while proc.poll() is None:
        output = proc.stdout.readline().decode('utf-8').replace('\r', '').replace('\n', '')
        if output != '':
            print(output)
    mvn_ret_code = proc.wait()  # catch return code
    if mvn_ret_code != 0:
        raise ValueError('Maven install returned error code %s' % str(mvn_ret_code))
    print('Maven install finished successfully!')


def read_blackstone(mc_version: str) -> Tuple[Mappings, MethodInheritanceTree]:
    blackstone = mapping_downloader.load_blackstone(mc_version)

    obf_to_moj = Mappings()
    method_inheritance = {}

    parse_blackstone(blackstone, obf_to_moj, method_inheritance)

    return obf_to_moj, method_inheritance


def parse_parchment(parchment: Dict[str, Any], named: Mappings):
    # Packages
    p_packages = utils.or_else(parchment, 'packages', [])
    for p_package in p_packages:
        named_package = named.add_package(p_package['name'])
        named_package.docs += utils.or_else(p_package, 'javadoc', [])

    # Classes
    p_classes = utils.or_else(parchment, 'classes', [])
    for p_class in p_classes:
        named_class = named.add_class(p_class['name'])
        named_class.docs += utils.or_else(p_class, 'javadoc', [])

        # Fields
        p_fields = utils.or_else(p_class, 'fields', [])
        for p_field in p_fields:
            named_field = named.add_field(named_class, p_field['name'], p_field['descriptor'])
            named_field.docs += utils.or_else(p_field, 'javadoc', [])

        # Methods
        p_methods = utils.or_else(p_class, 'methods', [])
        for p_method in p_methods:
            named_method = named.add_method(named_class, p_method['name'], p_method['descriptor'])
            named_method.docs += utils.or_else(p_method, 'javadoc', [])

            p_parameters = utils.or_else(p_method, 'parameters', [])
            for p_parameter in p_parameters:
                named_parameter = named.add_parameter(named_class, named_method, p_parameter['index'])
                named_parameter.mapped = utils.or_else(p_parameter, 'name')
                named_parameter.doc = utils.or_else(p_parameter, 'javadoc')


def parse_blackstone(blackstone: Dict[str, Any], obf_to_moj: Mappings, method_inheritance: MethodInheritanceTree):
    b_classes = utils.or_else(blackstone, 'classes', [])
    for b_class in b_classes:
        parse_blackstone_class(b_class, obf_to_moj, method_inheritance)


def parse_blackstone_class(b_class: Dict[str, Any], obf_to_moj: Mappings, method_inheritance: MethodInheritanceTree):
    # Class and package
    obf_class = b_class['name']['obf']
    moj_class = b_class['name']['moj']

    named_class = obf_to_moj.add_class(obf_class)
    named_class.mapped = moj_class

    # Inner classes
    b_inners = utils.or_else(b_class, 'inner', [])
    for b_inner in b_inners:
        parse_blackstone_class(b_inner, obf_to_moj, method_inheritance)

    # Fields
    b_fields = utils.or_else(b_class, 'fields', [])
    for b_field in b_fields:
        b_name = b_field['name']
        b_descriptor = b_field['descriptor']

        obf_field = b_name['obf']
        moj_field = b_name['moj']
        obf_desc = b_descriptor['obf']

        # Skip synthetic fields
        if (b_field['security'] & utils.ACC_SYNTHETIC) != 0:
            continue

        named_field = obf_to_moj.add_field(named_class, obf_field, obf_desc)
        named_field.mapped = moj_field

    # Methods
    b_methods = utils.or_else(b_class, 'methods', [])
    primary_methods = {}
    missing_methods = {}
    for b_method in b_methods:
        b_name = b_method['name']
        key = b_name['obf'], b_method['descriptor']['obf']
        if 'moj' in b_name:
            # Normal method
            primary_methods[key] = b_method
        else:
            missing_methods[key] = b_method

    # Iterate methods again, now with the ability to match primary -> missing to restore access flags
    for key, b_method in primary_methods.items():
        obf_method, obf_desc = key

        access_flags = b_method['security']
        if key in missing_methods:
            assert access_flags == 0
            access_flags = missing_methods[key]['security']

        # Skip synthetic methods, there is no point mapping their parameters. Include methods marked as lambdas.
        # The blackstone 'lambda' param is a heuristic, so we include them by default. There may be both synthetic and non-synthetic lambdas.
        if (access_flags & utils.ACC_SYNTHETIC) != 0 and not b_method['lambda']:
            continue

        moj_method = b_method['name']['moj']
        moj_desc = b_method['descriptor']['moj']

        _, param_types = utils.split_method_descriptor(moj_desc)

        named_method = obf_to_moj.add_method(named_class, obf_method, obf_desc)
        obf_to_moj.add_parameters_from_method(named_class, named_method, (access_flags & utils.ACC_STATIC) != 0)
        named_method.is_lambda = utils.or_else(b_method, 'lambda', named_method.is_lambda)
        named_method.mapped = moj_method

        if 'overrides' in b_method:
            method_inheritance[(obf_class, obf_method, obf_desc)] = set(b_override['owner']['obf'] for b_override in b_method['overrides'])
