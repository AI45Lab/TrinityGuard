import os 
from .run_workflow import run_evoagent_workflow

files = os.listdir('./workflow')

os.makedirs('./logs', exist_ok=True)

for file in files:
    logs = run_evoagent_workflow(f'./workflow/{file}')

    with open('./logs/' + file.split('.')[0] + '_summary.txt', 'w') as f:
        f.write(logs)