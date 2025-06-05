# Tableau LangChain Starter Kit
An implementation of Tableau LangChain for providing AI functionality Tableau Server or Cloud


### Setup virtual environment

```
python -m venv venv 
```

### Activate virtual environment

For windows:
```
venv\Scripts\activate
```

For Mac/Linux:
```
source venv/bin/activate
```

### Install Packages
```
pip install -r requirements.txt
```

### Setup .env file

A [template .env](.env_template) file is available, please update this with your details keeping the variable names (i.e. TABLEAU_DOMAIN) the same. 


Testing mode:
```
python main.py
```

Web interface and dashboard extension:
```
python web_app.py
```