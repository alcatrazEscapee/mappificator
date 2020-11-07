from mapping import srg_mapping, intermediary_mapping
from util import utils
from util.sources import SourceMap


def main(mc_version: str):
    srg, srg_indexed_params = srg_mapping.read(mc_version)
    intermediary = intermediary_mapping.read(mc_version)

    # srg has extra named classes for legacy reasons
    legacy_mcpconfig = {'afd', 'det'}

    def filter_legacy_mcpconfig(k, v):
        if isinstance(k, str):
            return k not in legacy_mcpconfig
        else:
            return k[0] not in legacy_mcpconfig

    srg = srg.filter(filter_legacy_mcpconfig)

    srg_v_intermediary = srg.keys().compare_to(intermediary.keys())

    # Assert srg v intermediary classes and fields match
    assert not srg_v_intermediary.right_only.classes
    assert not srg_v_intermediary.left_only.classes
    assert not srg_v_intermediary.right_only.fields
    assert not srg_v_intermediary.left_only.fields

    # Assert intermediary methods are a subset of srg
    assert not srg_v_intermediary.right_only.methods

    # Fix missing intermediary methods by matching identical srg methods
    inverse_srg = utils.invert_mapping(srg.methods)  # srg methods -> notch
    multiple_matches = set()
    no_matches = set()
    intermediary_methods = dict(intermediary.methods)
    for srg_method, notch_methods in inverse_srg.items():
        if not srg_method.startswith('func_'):
            continue  # skip non-srg named methods
        matches = set()
        for notch_method in notch_methods:
            if notch_method in intermediary.methods:
                matches.add(notch_method)
        if matches:
            if len(matches) == 1:
                # Exact match, add directly
                match = matches.pop()
                for notch_method in notch_methods:
                    intermediary_methods[notch_method] = intermediary.methods[match]
            else:
                for notch_method in notch_methods:
                    if notch_method not in intermediary.methods:
                        # Partial match
                        multiple_matches.add((srg_method, frozenset(notch_methods), frozenset(matches), frozenset(intermediary.methods[m] for m in matches)))
                        break
                else:
                    # Complete match - 1 srg -> multiple notch -> already mapped individually
                    pass
        else:
            no_matches.add((srg_method, frozenset(notch_methods)))

    intermediary = SourceMap(intermediary.fields, intermediary_methods, classes=intermediary.classes)

    srg_v_intermediary = srg.keys().compare_to(intermediary.keys())

    print('Done')


if __name__ == '__main__':
    main('1.16.3')
