import json

with open('main.py', 'r', encoding='utf-8') as f:
    agent_code = f.read()

writefile_content = '%%writefile submission.py\n' + agent_code

notebook = {
    'cells': [
        {
            'cell_type': 'markdown',
            'metadata': {},
            'source': [
                '# Kaggriculture V2 Strategic Planner Submission\n',
                '\n',
                'This notebook packages the self-contained V2 Strategic Planner agent into `submission.py` and runs a local verification game before submission.'
            ]
        },
        {
            'cell_type': 'code',
            'execution_count': None,
            'metadata': {},
            'outputs': [],
            'source': [
                '# 1. Install or update kaggle-environments\n',
                '!pip install -q -U kaggle-environments'
            ]
        },
        {
            'cell_type': 'code',
            'execution_count': None,
            'metadata': {},
            'outputs': [],
            'source': [writefile_content]
        },
        {
            'cell_type': 'code',
            'execution_count': None,
            'metadata': {},
            'outputs': [],
            'source': [
                '# 3. Test submission.py locally inside the notebook\n',
                'from kaggle_environments import make\n',
                '\n',
                'env = make("kaggriculture", configuration={"episodeSteps": 720}, debug=True)\n',
                'env.run(["submission.py", "random"])\n',
                '\n',
                'final = env.steps[-1]\n',
                'print(f"Player 0 (V2): ${final[0].reward} | Status: {final[0].status}")\n',
                'print(f"Player 1 (Random): ${final[1].reward} | Status: {final[1].status}")\n'
            ]
        },
        {
            'cell_type': 'code',
            'execution_count': None,
            'metadata': {},
            'outputs': [],
            'source': [
                '# 4. Optional: View the game replay\n',
                '# env.render(mode="ipython", width=1000, height=700)\n'
            ]
        }
    ],
    'metadata': {
        'language_info': {'name': 'python'}
    },
    'nbformat': 4,
    'nbformat_minor': 5
}

with open('kaggriculture_submission_notebook.ipynb', 'w', encoding='utf-8') as f:
    json.dump(notebook, f, indent=2)

print('Notebook created successfully!')
