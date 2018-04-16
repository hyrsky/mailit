from unittest.mock import MagicMock
import pytest
import types
import mailit
import io

NORMAL_FILE = 'email,first_name,last_name\ntest@example.com,test,case'
OBSCURE_EMAIL_FIELD = 'foobar,first_name,last_name\ntest@example.com,test,case'

def create_mock_csvfile(content):
    csvfile = io.StringIO(content)

    return csvfile

def test_csvfile_to_recipients():
    file_mock = create_mock_csvfile(NORMAL_FILE)
    generator = mail.csvfile_to_recipients(file_mock, email_field='email')

    assert isinstance(generator, types.GeneratorType)

    values = list(generator)
    assert len(values) == 1
    assert values[0].email == "test@example.com"
    assert values[0].first_name == "test"
    assert values[0].last_name == "case"

def test_csvfile_to_recipients_autodetect_field_name():
    file_mock = create_mock_csvfile(OBSCURE_EMAIL_FIELD)
    generator = mail.csvfile_to_recipients(file_mock)

    assert isinstance(generator, types.GeneratorType)

    values = list(generator)
    assert len(values) == 1
    assert values[0].email == "test@example.com"
