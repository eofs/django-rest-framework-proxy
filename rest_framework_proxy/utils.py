import mimetypes

from requests.packages.urllib3.filepost import choose_boundary


def generate_boundary():
    return choose_boundary()

class StreamingMultipart(object):
    def __init__(self, data, files, boundary, chunk_size = 1024):
        self.data = data
        self.files = files
        self.boundary = boundary
        self.itering_files = False
        self.chunk_size = chunk_size

    def __len__(self):
        # TODO Optimize as currently we are iterating data and files twice
        # Possible solution: Cache body into file and stream from it
        size = 0
        for i in self.__iter__():
            size += len(i)
        return size

    def __iter__(self):
        return self.generator()

    def generator(self):
        for (k, v) in self.data.items():
            yield b'%s\r\n\r\n' % self.build_multipart_header(k)
            yield b'%s\r\n' % v

        for (k, v) in self.files.items():
            content_type = mimetypes.guess_type(v.name)[0] or 'application/octet-stream'
            yield b'%s\r\n\r\n' % self.build_multipart_header(k, v.name, content_type)

            # Seek back to start as __len__ has already read the file
            v.seek(0)

            # Read file chunk by chunk
            while True:
                data = v.read(self.chunk_size)
                if not data:
                    break
                yield data
            yield b'\r\n'
        yield self.build_multipart_footer()

    def build_multipart_header(self, name, filename=None, content_type=None):
        output = []
        output.append('--%s' % self.boundary)

        string = 'Content-Disposition: form-data; name="%s"' % name
        if filename:
            string += '; filename="%s"' % filename
        output.append(string)

        if content_type:
            output.append('Content-Type: %s' % content_type)

        return b'\r\n'.join(output)

    def build_multipart_footer(self):
        return b'--%s--\r\n' % self.boundary
