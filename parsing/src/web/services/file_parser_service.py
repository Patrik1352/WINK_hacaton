import json
import pandas as pd
from tqdm import tqdm

# from utils import nuextract_model


class FileParserService:
    def __init__(self, output_columns: list, extract_model_class) -> None:
        self.df = pd.DataFrame()        
        self.output_columns = output_columns 
        self.extract_model_class = extract_model_class
        
    # def start(self):
    #     self.extract_model_class.init_model()
    
    # def stop(self):
    #     self.extract_model_class.stop_model()
    
    def parse_file(self, file_path) -> pd.DataFrame:
        with open(file_path, 'r') as f:
            self.loaded_document = json.load(f)
    
        for scene_i in tqdm(range(len(self.loaded_document))):
            full_scene = str(self.loaded_document[scene_i]['id']) + ' ' + self.loaded_document[scene_i]['title'] + ' ' + self.loaded_document[scene_i]['text']
            parsed_scene = json.loads(self.extract_model_class.parse(full_scene)[0])
            if self.df.empty:
                self.df = pd.DataFrame({key: [value] for key, value in parsed_scene.items()})
            else:
                df_new = pd.DataFrame({key: [value] for key, value in parsed_scene.items()})
                self.df = pd.concat([self.df, df_new]).reset_index(drop=True)
        
        return self.df[self.output_columns]