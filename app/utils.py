import pandas as pd
import random

def get_history_data(counts = 100, offset=0):
    df_a = pd.DataFrame({
        'PID':range(0, 100),
        'Inserted': pd.date_range('2023-01-01', periods=counts, freq="1H"),
        'Metric': random.choices(range(1, 50), k=counts),
        'Table': ['A'] * counts,
        'Status': ['used'] * counts
    })
    df_b = pd.DataFrame({
        'PID':range(100, 200),
        'Inserted': pd.date_range('2023-01-01', periods=counts, freq="1H"),
        'Metric': random.choices(range(1, 50), k=counts),
        'Table': ['B'] * counts,
        'Status': ['used'] * counts
    })
    df_c = pd.DataFrame({
        'PID':range(200, 300),
        'Inserted': pd.date_range('2023-01-01', periods=counts, freq="1H"),
        'Metric': random.choices(range(1, 50), k=counts),
        'Table': ['C'] * counts,
        'Status': ['used'] * counts
    })
    return pd.concat([df_a, df_b, df_c], join="inner")