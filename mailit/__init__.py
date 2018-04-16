#!/usr/bin/env python

import logging
import mandrill
import mimetypes
import itertools
import argparse
import base64
import sys
import csv
import os
import re

from collections import namedtuple

class Recipient:
    """Recipient data structure

    Recipient must have an ``email`` address, other fields are optional.
    All other fields are included to recipient specific merge tags.

    ``first_name``, ``last_name`` and ``name`` are special fields that specify
    name that is displayed to recipient by most clients. If set, ``name`` is
    used, otherwise full name is used if both ``first_name`` and ``last_name``
    is set and only first_name is used if no ``last_name`` is set.
    """
    def __init__(self, email, **kwargs):
        def name():
            if kwargs.get('first_name') and kwargs.get('last_name'):
                return '%s %s' % (kwargs.get('first_name'), kwargs.get('last_name'))
            elif kwargs.get('first_name'):
                return kwargs.get('first_name')
            return ''

        self.email = email
        self.first_name = kwargs.get('first_name')
        self.last_name = kwargs.get('last_name')
        self.name = kwargs.get('name', name()).title()

        self.merge_vars = [{
            "name": key.upper(),
            "content": kwargs[key]
        } for key in kwargs]

    def __repr__(self):
        return "%s<%s>" % (__class__.__name__, self.email)

class Mail:
    """Mail object

    Used to send HTML email templates
    """
    def __init__(self, api_key, subject, from_name, from_email, **kwargs):
        """Mail constructor

        Note that ``from_email`` must be verified by Mandrill.

        Args:
            api_key (str): Mandrill api key
            subject (str): email subject
            from_name (str): email from name
            from_email (str): email from address
        """
        self._client = mandrill.Mandrill(api_key)
        self._logger = logging.getLogger('mail')

        # Set empty defaults
        self.clear()

        self.template = kwargs.get('template')
        self._subject = subject
        self._from_email = from_email
        self._from_name = from_name

    def clear(self):
        self._template = None
        self._images = {}
        self._merge_vars = []
        self._subject = ''
        self._from_email = ''
        self._from_name = ''

    @property
    def template(self):
        return self._template

    @template.setter
    def template(self, template):
        if isinstance(template, str):
            self._template = template
        else:
            self._template = template.read()  # template is file-like

    @property
    def global_merge_vars(self):
        return self._merge_vars

    def add_global_merge_var(self, name, content):
        # Convert merge vars to internal format
        self._merge_vars.append({
            "name": name.upper(),
            "content": content
        })

    def remove_global_merge_var(self, name):
        def first_true(iterable, default=False, pred=None):
            """Returns the first true value in the iterable.

            If no true value is found, returns ``default``

            If ``pred`` is not None, returns the first item
            for which pred(item) is true.

            >>> first_true([a,b,c], x) --> a or b or c or x
            >>> first_true([a,b], x, f) --> a if f(a) else b if f(b) else x
            """
            return next(filter(pred, iterable), default)

        name = name.upper()

        # Convert merge vars to internal format
        self._merge_vars.remove(first_true(
            self._merge_vars, pred=lambda x: x.get('name') == name))

    def add_image(self, filename, file=None, mimetype=None):
        """Add image to email template

        If ``file`` is specified parameter ``mimetype`` is required
        and ``filename`` is not opened. Otherwise file is read and
        type is guessed from file extension.

        In the template ``<img src="cid:image_name">`` can be used to
        reference the image, where ``image_name`` is ``filename`` without
        extension or path.

        Subsequent calls override previous files with the same ``filename``

        Args:
            filename (str): Filename
            file (file, optional): File pointer
            mimetype (str, optional): Image mime type
        """
        if mimetype is None:
            mimetype = mimetypes.guess_type(filename)[0]

        name = os.path.splitext(os.path.basename(filename))[0]

        if file is None:
            with open(filename, 'rb') as file:
                content = file.read()
        else:
            content = file.read()

        self._logger.debug("Add resource %s (%s)", filename, mimetype)

        self._images[name] = {
            "content": base64.b64encode(content).decode(),
            "type": mimetype,
            "name": name
        }

    def remove_image(self, filename):
        """Remove image to email template"""

        self._logger.debug("Remove resource %s", filename)

        del self._images[filename]

    @property
    def images(self):
        """Get image currently in template

        Use ``add_image`` and ``remove_image`` to modify images.

        Returns:
            dict(filename: object): A dictionary containing images. Keys
                are image filenames and values are in internal data structure
        """
        return self._images

    def send(self, recipients, batch_size=50, dry_run=False):
        """Send emails

        Args:
            recipients (iter(Recipient)): Iteratable recipients
            batch_size (int): Size of each batch. Defaults to 50.
            subject (str): Set email subject
            dry_run (bool): If true don't send email. Default to off.
        """

        dry_run and self._logger.warning('dry run in active')

        self._logger.info("Sending email \"%s\" from %s <%s>, %d images, %d global merge tags", 
                          self._subject, self._from_name, self._from_email,
                          len(self._images.keys()), 
                          len(self.global_merge_vars))

        recipients = iter(recipients)
        result = []

        def grouper(iterable, n, fillvalue=None):
            """Collect data into fixed-length chunks or blocks
            >>> grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
            """
            args = [iter(iterable)] * n
            return itertools.zip_longest(*args, fillvalue=fillvalue)

        for batch in grouper(recipients, batch_size):
            # Compose recipients and recipient specific merge vars structures
            to, merge_vars = zip(*(({
                'name': recipient.name,
                'email': recipient.email,
                'type': 'to'
            }, {
                'rcpt': recipient.email,
                'vars': recipient.merge_vars
            }) for recipient in batch if recipient is not None))

            self._logger.info('Sending batch to %d addresses', len(to))
            self._logger.debug('Batch recipients: %s', list(x.email for x in batch if x is not None))

            message = {
                'from_email': self._from_email,
                'from_name': self._from_name,
                'to': list(to),
                # whether or not to expose all recipients in to "To" header for each email
                'preserve_recipients': False,
                'subject': self._subject,
                'headers': {},
                'auto_html': None,
                'auto_text': None,
                'important': False,
                'inline_css': None,
                'merge': True,
                'merge_language': 'mailchimp',
                'global_merge_vars': self.global_merge_vars,
                'merge_vars': list(merge_vars),
                'html': self._template,
                'images': list(self._images.values()),
                'recipient_metadata': [],
                'tags': [],
                'url_strip_qs': None,
            }

            if not dry_run:
                result.append(self._client.messages.send(message=message))

        return result

def csvfile_to_recipients(csvfile, email_field=None):
    """csvfile_to_recipients(file) -> generator<Recipients>"""
    header = csvfile.readline()
    dialect = csv.Sniffer().sniff(header)
    reader = csv.reader(csvfile, dialect)

    header = header.replace(' ', '_').replace(dialect.delimiter, ' ').lower()
    header = ''.join(c for c in header if c.isalnum() or c in ['_', ' '])
    Row = namedtuple('Row', header)

    # Find email field when reading first line
    if email_field is None:
        data = Row(*next(reader))

        # Select first field that looks like email address
        for field in Row._fields:
            if re.match(r"[^@]+@[^@]+\.[^@]+", getattr(data, field)):
                email_field = field
                break

        # Still no email_field :(
        if email_field is None:
            raise Exception('Could not guess email field.')

        kwargs = {}
        kwargs.update(data._asdict())
        kwargs.update({"email": getattr(data, email_field)})
        yield Recipient(**kwargs)

    for data in map(Row._make, reader):
        kwargs = {}
        kwargs.update(data._asdict())
        kwargs.update({"email": getattr(data, email_field)})
        yield Recipient(**kwargs)

def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("template", type=argparse.FileType('r'),
                        help="email template file")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="increase output verbosity")
    parser.add_argument("--file", type=argparse.FileType('r', encoding='UTF-8'), default=sys.stdin,
                        help="read recipients from file instead of standard input")
    parser.add_argument("--email-field", metavar='FIELD',
                        help="email field name in input file. default = autodetect")
    parser.add_argument("--images", type=lambda x: x.split(','),
                        help="a comma separated list of files for templating")
    parser.add_argument("--var", nargs=2, action='append', metavar=('NAME', 'VALUE'),
                        help="global merge variable for template")
    parser.add_argument("--api-key", default=os.environ.get('MANDRILL_API_KEY'),
                        help="override MANDRILL_API_KEY environment variable")
    parser.add_argument("--dry-run", action="store_true",
                        help="perform a trial run with no changes made")
    parser.add_argument("--from-name", required=True, metavar="NAME",
                        help="email from name")
    parser.add_argument("--from", required=True, metavar="EMAIL",
                        help="email from address")
    parser.add_argument("--subject", required=True, help="email subject")

    return parser.parse_args()

def main():
    args = _parse_args()

    # Configure logging
    logLevel = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=logLevel)

    mailer = Mail(args.api_key, from_email=getattr(args, 'from'),
                  from_name=args.from_name, template=args.template,
                  subject=args.subject)

    # Convert global merge vars to internal format
    if args.var:
        for variable in args.var:
            mailer.add_global_merge_var(variable[0], variable[1])

    if args.images:
        for filename in args.images:
            mailer.add_image(filename=filename)

    recipients = csvfile_to_recipients(args.file, email_field=args.email_field)

    print(mailer.send(recipients, dry_run=args.dry_run))

if __name__ == '__main__':
    main()
