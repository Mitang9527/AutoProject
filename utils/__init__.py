
from utils.readFilesUtils.yamlControl import GetYamlData
from common.setting import ensure_path_sep
from utils.otherUtils.models import Config
import sys

args = sys.argv
config_name = "config.yaml"
if len(args) > 1 and args[1].__contains__("config.yaml"):
    config_name = args[1]

print(">>>>>>>>>>>>>>> load config file: {} >>>>>>>>>>>>>>>>".format(config_name))

_data = GetYamlData(ensure_path_sep("\\common\\" + config_name)).get_yaml_data()
config = Config(**_data)

