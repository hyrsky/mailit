from unittest.mock import MagicMock

import io
import mailit

def create_image():
    return io.BytesIO(b'\xff\xd8\xff\xFF\xFF')

def create_Mail():
    mail.mandrill.Mandrill = MagicMock(return_value='mock_client')
    return mail.Mail('api-key', subject='subject', from_name='from_name', from_email='from_email', template='string template')

def test_Mail_global_merge_vars():
    client = create_Mail()
    client.add_global_merge_var("test", "value")
    client.add_global_merge_var("another-test", "another-value")

    assert len(client.global_merge_vars) == 2

    client.remove_global_merge_var("another-test")
    assert len(client.global_merge_vars) == 1
    assert {"name": "TEST", "content": "value"} in client.global_merge_vars

    
def test_Mail_images():
    client = create_Mail()
    client.add_image(filename="image1", file=create_image(), mimetype='image/jpeg')
    client.add_image(filename="image2", file=create_image(), mimetype='image/jpeg')

    assert len(client.images) == 2

    client.remove_image("image2")
    assert len(client.images) == 1
    assert "image1" in client.images
