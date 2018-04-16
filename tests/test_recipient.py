import mailit

def test_Recipient():
    recipient = mail.Recipient('test@example.com')
    assert recipient.email == 'test@example.com'

def test_Recipient_merge_tags():
    recipient = mail.Recipient('test@example.com', first_name='Jane', value='10 €')
    assert len(recipient.merge_vars) == 2
    assert {"name": "VALUE", "content": "10 €"} in recipient.merge_vars

def test_Recipient_name():
    recipient = mail.Recipient('test@example.com', name='John Smith')
    assert recipient.name == 'John Smith'
    recipient = mail.Recipient('test@example.com', first_name='Jane', last_name='Smith')
    assert recipient.name == 'Jane Smith'
    recipient = mail.Recipient('test@example.com', first_name='Jane')
    assert recipient.name == 'Jane'
    recipient = mail.Recipient('test@example.com', last_name='Smith')
    assert recipient.name == ''
