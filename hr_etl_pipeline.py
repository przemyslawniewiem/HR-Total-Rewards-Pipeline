import pandas as pd
import numpy as np
import logging
from typing import Tuple

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("HRPipeline")

class HREtlPipeline:
    def __init__(self, num_employees: int = 200, seed: int = 42):
        self.num_employees = num_employees
        self.seed = seed
        np.random.seed(self.seed)
        
    def extract_mock_data(self) -> pd.DataFrame:
        departments = ['IT', 'Finance', 'HR', 'Sales', 'Marketing']
        data = []
        
        for i in range(1, self.num_employees + 1):
            dept = np.random.choice(departments)
            base_salary = np.random.normal(loc=12000 if dept == 'IT' else 8000, scale=2000)
            
            if i in [15, 88, 142]: 
                base_salary *= 10  
            elif i in [42, 105]:
                base_salary = 500  
                
            data.append({
                'Employee_ID': f"EMP{str(i).zfill(4)}",
                'Department': dept,
                'Role': 'Specialist',
                'Current_Salary_PLN': round(base_salary, 2),
                'Contract_Type': np.random.choice(['B2B', 'UoP']),
                'Last_Bonus_PLN': round(np.random.uniform(0, 5000), 2)
            })
        
        df = pd.DataFrame(data)
        df.loc[10:15, 'Contract_Type'] = np.nan 
        
        logger.info(f"Extracted mock data for {self.num_employees} employees.")
        return df

    def transform_and_detect_anomalies(self, df: pd.DataFrame) -> pd.DataFrame:
        df['Contract_Type'] = df['Contract_Type'].fillna('UoP')
        
        df['Dept_Mean'] = df.groupby('Department')['Current_Salary_PLN'].transform('mean')
        df['Dept_Std'] = df.groupby('Department')['Current_Salary_PLN'].transform('std')
        
        df['Z_Score'] = (df['Current_Salary_PLN'] - df['Dept_Mean']) / df['Dept_Std']
        df['Is_Anomaly'] = np.where(df['Z_Score'].abs() > 2, True, False)
        
        df.drop(columns=['Dept_Mean', 'Dept_Std', 'Z_Score'], inplace=True)
        
        anomalies_count = df['Is_Anomaly'].sum()
        logger.info(f"Transformation complete. Detected {anomalies_count} payroll anomalies.")
        return df

    def calculate_forecast(self, df: pd.DataFrame, inflation_rate: float = 0.05, it_adjustment: float = 0.08) -> pd.DataFrame:
        df['Forecasted_Salary'] = df['Current_Salary_PLN'] * (1 + inflation_rate)
        df.loc[df['Department'] == 'IT', 'Forecasted_Salary'] *= (1 + it_adjustment)
        
        df['Forecasted_Salary'] = df['Forecasted_Salary'].round(2)
        df['Budget_Increase_PLN'] = df['Forecasted_Salary'] - df['Current_Salary_PLN']
        
        logger.info("Applied financial forecasting scenarios.")
        return df

    def _create_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        summary = df.groupby('Department').agg(
            Headcount=('Employee_ID', 'count'),
            Current_Budget=('Current_Salary_PLN', 'sum'),
            Forecasted_Budget=('Forecasted_Salary', 'sum')
        ).reset_index()
        return summary

    def load_to_excel_with_charts(self, df: pd.DataFrame, output_path: str):
        summary_df = self._create_summary(df)
        anomalies_df = df[df['Is_Anomaly'] == True]
        
        writer = pd.ExcelWriter(output_path, engine='xlsxwriter')
        
        df.to_excel(writer, sheet_name='Data_Forecast', index=False)
        anomalies_df.to_excel(writer, sheet_name='Anomalies', index=False)
        summary_df.to_excel(writer, sheet_name='Budget_Summary', index=False)
        
        workbook = writer.book
        summary_sheet = writer.sheets['Budget_Summary']
        
        chart = workbook.add_chart({'type': 'column'})
        
        num_rows = len(summary_df)
        
        # Seria 1: Obecny budżet
        chart.add_series({
            'name':       ['Budget_Summary', 0, 2],
            'categories': ['Budget_Summary', 1, 0, num_rows, 0],
            'values':     ['Budget_Summary', 1, 2, num_rows, 2],
            'fill':       {'color': '#4F81BD'}
        })
        
        # Seria 2: Prognozowany budżet
        chart.add_series({
            'name':       ['Budget_Summary', 0, 3],
            'categories': ['Budget_Summary', 1, 0, num_rows, 0],
            'values':     ['Budget_Summary', 1, 3, num_rows, 3],
            'fill':       {'color': '#C0504D'}
        })
        
        chart.set_title({'name': 'Current vs Forecasted Budget by Department'})
        chart.set_x_axis({'name': 'Department'})
        chart.set_y_axis({'name': 'Budget (PLN)'})
        chart.set_size({'width': 700, 'height': 400})
        
        summary_sheet.insert_chart('F2', chart)
        
        writer.close()
        logger.info(f"Report successfully generated at: {output_path}")

    def run_pipeline(self, output_filename: str):
        logger.info("Starting HR ETL Pipeline...")
        raw_data = self.extract_mock_data()
        clean_data = self.transform_and_detect_anomalies(raw_data)
        forecast_data = self.calculate_forecast(clean_data)
        self.load_to_excel_with_charts(forecast_data, output_filename)
        logger.info("Pipeline execution finished.")


if __name__ == "__main__":
    pipeline = HREtlPipeline(num_employees=500)
    pipeline.run_pipeline("HR_Total_Rewards_Forecast.xlsx")