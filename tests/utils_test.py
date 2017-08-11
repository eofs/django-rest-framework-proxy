import requests

from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.http.request import QueryDict
from django.test import TestCase
from mock import Mock, patch

from rest_framework_proxy.utils import StreamingMultipart


class StreamingMultipartTests(TestCase):

    def test_generator(self):
        upload_bstr = b'test binary data'
        upload_file = BytesIO()
        upload_file.write(upload_bstr)
        upload_file.seek(0)
        upload_data = InMemoryUploadedFile(upload_file,
                                           'file',
                                           'test_file.dat',
                                           'application/octet-stream',
                                           len(upload_bstr),
                                           None,
                                           content_type_extra={})

        data = QueryDict(mutable=True)
        data['file'] = upload_data
        files = {'file': upload_data}
        boundary = 'ddd37654bd80490fa3c58987954aa380'

        streamingMultiPart = StreamingMultipart(data, files, boundary)
        generator = streamingMultiPart.generator()


        data_mpheader = next(generator)
        expected_data_mpheader = b'--ddd37654bd80490fa3c58987954aa380\r\nContent-Disposition: form-data; name="file"\r\n\r\n'
        self.assertEqual(data_mpheader, expected_data_mpheader)

        data_body = next(generator)
        expected_data_body = b'test_file.dat\r\n'
        self.assertEqual(data_body, expected_data_body)

        file_mpheader = next(generator)
        expected_file_mpheader = b'--ddd37654bd80490fa3c58987954aa380\r\nContent-Disposition: form-data; name="file"; filename="test_file.dat"\r\nContent-Type: application/octet-stream\r\n\r\n'
        self.assertEqual(file_mpheader, expected_file_mpheader)

        file_body = next(generator)
        expected_file_body = b'test binary data'
        self.assertEqual(file_body, expected_file_body)
        self.assertEqual(next(generator), b'\r\n')

        mpfooter = next(generator)
        expected_mpfooter = b'--ddd37654bd80490fa3c58987954aa380--\r\n'
        self.assertEqual(mpfooter, expected_mpfooter)

        try:
            v = next(generator)
            self.fail('Unexpected iteration - %r' % v)
        except StopIteration:
            pass
