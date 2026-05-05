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