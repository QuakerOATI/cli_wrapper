import json
import yaml
from pathlib import Path


# TODO: Allow this file to move around by replacing this with something like
# sys.modules['__main__'] (requires changing the driver entry point)
PROJECT_ROOT = Path(__file__).parent
ROOT_CONFIG_FILE = Path(PROJECT_ROOT, "configuration.json")


def _merge_dicts(obj: dict, update: dict) -> dict:
    """Recursively merge update into obj and return the result.

    If a key is found in both obj and update, the merged dict has
        merged[key] == update[key].

    Args:
        obj (dict): dict object to update
        update (dict): updates to be applied recursively to obj

    Returns:
        :obj:`dict`: the recursively-merged dict
    """
    # NOTE: It is important to allow update to contain None values
    if not isinstance(update, dict) or not isinstance(obj, dict):
        return update
    result = {}
    for key, value in obj.items():
        try:
            result[key] = _merge_dicts(value, update[key])
        except KeyError:
            result[key] = value
    return result


def build_config_file(*filenames: str) -> dict:
    """Merge config objects in files and write results to ROOT_CONFIG_FILE.

    Configuration files may be formatted as either JSON or YAML.

    Args:
        *files: List of configuration files to merge in lowest-to-highest
            order of precedence, i.e., passing 'config1.json', 'config2.json'
            would result in any conflicts between config1 and config2 being
            resolved in favor of config2.  Files ending in ".json" will be
            assumed to contain valid JSON; files ending in ".yml" or ".yaml"
            will be assumed to contain valid YAML.

    Returns:
        :obj:`dict`: dict containing the merged configuration data

    Side effects:
        The merged configuration object is written to configuration.json.

    Raises:
        ValueError: if one of the passed filenames does not have a JSON or
            YAML extension
    """
    obj = {}
    for file in filenames:
        path = Path(file)
        with path.open("r") as stream:
            if path.suffix == ".json":
                file_obj = json.load(stream)
            elif path.suffix in (".yaml", ".yml"):
                file_obj = yaml.safe_load(stream)
            else:
                raise ValueError(
                    f"Configuration file suffix should be .json, .yml, or .yaml, not {path.suffix!r}"
                )
            obj = _merge_dicts(obj, file_obj)

    with open(ROOT_CONFIG_FILE, "w") as ostream:
        json.dump(obj, ostream, indent=2)
    return obj
