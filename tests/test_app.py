import os
import pytest
import json
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_get_workflow(client):
    response = client.get('/workflow/test_workflow')
    assert response.status_code == 200
    data = response.get_json()
    assert 'workflowName' in data

def test_update_workflow(client):
    payload = {
        "workflowName": "UpdatedWorkflow",
        "global": {
            "userId": "67890",
            "token": "newtoken123"
        }
    }
    response = client.put('/workflow/test_workflow', json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data['workflow']['workflowName'] == "UpdatedWorkflow"

def test_add_step(client):
    payload = {
        "name": "step1",
        "method": "GET",
        "url": "http://example.com",
        "headers": {},
        "body": {},
        "dependsOn": [],
        "validations": []
    }
    response = client.post('/workflow/test_workflow/steps', json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data['step']['method'] == "GET"

def test_delete_step(client):
    response = client.delete('/workflow/test_workflow/steps/step1')
    assert response.status_code == 200
    data = response.get_json()
    assert "Step 'step1' deleted" in data['message']

def test_update_step(client):
    payload = {
        "method": "POST",
        "url": "http://example.com/update",
        "headers": {"Content-Type": "application/json"},
        "body": {"key": "value"},
        "dependsOn": ["step1"],
        "validations": [{"target": "status", "operator": "equals", "value": 200}]
    }
    response = client.put('/workflow/test_workflow/steps/step1', json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data['step']['url'] == "http://example.com/update"

def test_execute_step(client):
    response = client.post('/workflow/test_workflow/steps/step1/execute')
    assert response.status_code == 200
    data = response.get_json()
    assert 'result' in data

def test_list_workflows(client):
    response = client.get('/workflows')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)