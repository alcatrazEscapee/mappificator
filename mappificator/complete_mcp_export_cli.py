# This is a simple python CLI, similar to K9 that is able to use the log file to help give diagnostic information about mappings
# The primary use is during development - to find conflicting param names or methods, or to be able to add manual mappings directly
# Each command is a space separated series of statements. These statements will either provide a set of results, or mutate one
# The results will be displayed at the end of each statement
# Commands:
# nc <name> - lists notch class names matching <name>
# c <name> - lists srg class names matching <name>
# m <name> - lists named methods matching <name>
# f <name> - lists named fields matching <name>
# p <name> - lists named params matching <name>
# fc <name> - filters the results (methods, fields, or params) by the class <name>
# fm <name> - filters the results (params) by the method <name>
# [ <index> - only includes a single entry, at index <index> of the previous results
# ^ - copies the previous command
# gm - takes the first class from the previous results and returns all matching methods
# gp - takes the first param from the previous results and returns all matching params


from mappificator.make_complete_mcp_export import VERSION
from mappificator.util.mapping_downloader import CACHE_ROOT


def main():
    print('Loading...')

    with open(CACHE_ROOT + 'mcp_snapshot-%s.log' % VERSION) as f:
        log = f.read()

    sources = []
    for line in log.split('\n'):
        if line != '':
            sources.append(tuple(line.split('\t')))
    indexed = {'C': [], 'F': [], 'M': [], 'P': []}
    for s in sources:
        indexed[s[0]].append(s)

    print('Complete MCP Export CLI')

    cmd = input('>')
    prev_parts = []
    while cmd != 'exit':
        try:
            results = []
            cmd_parts = [c.lower() for c in cmd.split(' ')]
            if cmd_parts[0] == '^':
                cmd_parts = prev_parts + cmd_parts[1:]
            max_show = 10
            index = 0
            while index < len(cmd_parts):
                cmd_part = cmd_parts[index]
                if cmd_part == 'c':  # list classes
                    clazz = cmd_parts[index + 1]
                    results = [i for i in indexed['C'] if clazz in i[2].lower()]
                elif cmd_part == 'nc':  # list notch classes
                    clazz = cmd_parts[index + 1]
                    results = [i for i in indexed['C'] if clazz in i[1].lower()]
                elif cmd_part == 'f':  # list fields
                    field = cmd_parts[index + 1]
                    results = [i for i in indexed['F'] if field in i[2].lower()]
                elif cmd_part == 'm':  # list methods
                    method = cmd_parts[index + 1]
                    results = [i for i in indexed['M'] if method in i[2].lower()]
                elif cmd_part == 'p':  # list params
                    param = cmd_parts[index + 1]
                    results = [i for i in indexed['P'] if param in i[4].lower()]
                elif cmd_part == 'fc':  # filter classes (on a field, method or class search)
                    clazz = cmd_parts[index + 1]
                    results = [r for r in results if clazz in r[1].lower()]
                elif cmd_part == 'fm':  # filter methods (on a param search)
                    method = cmd_parts[index + 1]
                    results = [r for r in results if method in r[2].lower()]
                elif cmd_part == '[':  # picks a single result
                    i = int(cmd_parts[index + 1])
                    results = [results[i]]
                elif cmd_part == 'gp':  # gets parameters for the first method name
                    method = results[0]
                    results = [p for p in indexed['P'] if method[1] == p[1] and method[2] == p[2]]
                    index -= 1
                elif cmd_part == 'gm':  # gets methods for each class
                    clazz = results[0]
                    results = [m for m in indexed['M'] if clazz[2] == m[1]]
                    index -= 1
                elif cmd_part == 'max':  # max results returned
                    max_show = int(cmd_parts[index + 1])

                index += 2

            for r in results[:max_show]:
                print(r)
            if len(results) > max_show:
                print('First %d results shown. Use max # for more' % max_show)
            if not results:
                print('No Results')
            prev_parts = cmd_parts
        except Exception as e:
            print('Error: ' + str(e))
        cmd = input('>')


if __name__ == '__main__':
    main()
