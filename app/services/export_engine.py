import pandas as pd
import io

class ExportEngine:
    @staticmethod
    def to_excel(data_list: list, filename: str):
        df = pd.DataFrame(data_list)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='MimikaDataHub_Clean')
        output.seek(0)
        return output

    @staticmethod
    def list_to_excel(data_list: list, sheet_name: str):
        df = pd.DataFrame(data_list)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name=sheet_name)
        output.seek(0)
        return output
    
    @staticmethod
    def list_to_csv(data_list: list):
        df = pd.DataFrame(data_list)
        return df.to_csv(index=False).encode('utf-8')