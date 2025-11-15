import sys
sys.path.insert(0, '/home/yc-user/MIKHAIL/WINK_hacaton/parsing/src/web')
from services.file_parser_service import FileParserService
from utils.nuextract_model import NuExtract

model = NuExtract()
file_parser = FileParserService(["Сцена", "Режим"], model)
file_path = "/home/yc-user/MIKHAIL/WINK_hacaton/parsing/src/web/tests/ПТ_С12_Д_30.06.json"
df = file_parser.parse_file(file_path)
print(df.head())

