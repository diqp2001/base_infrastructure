""" 
Environnement
https://code.visualstudio.com/docs/python/environments

Debugging
https://code.visualstudio.com/docs/python/debugging

Testing
https://code.visualstudio.com/docs/python/testing



py -m pip install optuna
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
pip freeze > requirements.txt
py -m unittest discover -s src/tests -p "test_*.py" -v
.venv\Scripts\Activate.ps1
deactivate
pip list
pip install -r requirements.txt
pip freeze > requirements.txt

""" 