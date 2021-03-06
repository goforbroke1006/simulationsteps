import json
import time
import re

from simulationsteps.validators import validate_postgres, validate_redis, validate_openapi


def calculate_time(timestamp_formula):
    m = re.search('now([+\\-\\d]+)seconds', timestamp_formula)
    if m:
        seconds = m.group(1)
        return int(time.time()) + int(seconds)
        # return calendar.timegm(datetime.now().utctimetuple()) + int(seconds)
    else:
        return int(timestamp_formula)
    pass


def replace_placeholders(variables, val_raw):
    # print('val_raw (%s) = %s' % (type(val_raw), val_raw))

    if not isinstance(val_raw, str):
        return val_raw

    for n in variables:
        value = str(variables[n])
        placeholder = '%' + n + '%'
        # print('try replace %s with %s' % (placeholder, value))
        val_raw = val_raw.replace(placeholder, value)

    # print('val_raw (%s) = %s' % (type(val_raw), val_raw))
    return str(val_raw)
    pass


def patch_context(context, config_filename, custom_validators_fn: {}):
    """
    Append targets configs that imported from config file
    :type context: behave.runner.Context
    :type config_filename: str
    :type custom_validators_fn: dict
    :return: None
    """

    f = open(config_filename, "r")
    config = json.loads(f.read())

    context.simulation = type('', (), {})()
    context.simulation.targets = {}

    validators_fn = {
        'postgres': validate_postgres,
        'redis': validate_redis,
        'openapi': validate_openapi,
    }
    for cv_type in custom_validators_fn:
        validators_fn[cv_type] = custom_validators_fn[cv_type]

    for t in config['targets']:
        target_type = t['type']
        target_name = t['name']
        target_config = t['config']

        if target_type not in context.simulation.targets:
            context.simulation.targets[target_type] = {}

        if target_name in context.simulation.targets[target_type]:
            raise Exception(f'target {target_name} already exists')

        if target_type in validators_fn:
            validator = validators_fn[target_type]
            validator(t)
        else:
            raise Exception(f'can\'t fount validator for target type "{target_type}"')

        context.simulation.targets[target_type][target_name] = target_config
        print(f'{target_name} ({target_type}) loaded')

    pass


def read_process(process):
    stdout = ''
    stderr = ''

    for line in process.stdout:
        stdout += line.decode("utf-8")

    for line in process.stderr:
        stderr += line.decode("utf-8")

    return stdout, stderr


def json_has_subset(target, subset):
    def recursive_check_subset(a, b):
        for x in a:
            if not isinstance(a[x], dict):
                yield (x in b) and (a[x] == b[x])  # return a bool
            else:
                if x in b:
                    yield all(recursive_check_subset(a[x], b[x]))
                else:
                    yield False

    return all(recursive_check_subset(target, subset))


def json_get_value(content, path):
    from jsonpath_ng import parse
    jsonpath_expr = parse(path)

    if isinstance(content, str):
        content = json.loads(content)

    extracted = [match.value for match in jsonpath_expr.find(content)]

    return extracted
