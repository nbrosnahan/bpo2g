def test_dummy():
    assert True

def process_data(data):
    return { "processed": True }

def test_process_data(sample_data):
    # The fixture is automatically injected
    result = process_data(sample_data)
    assert result["processed"] == True
