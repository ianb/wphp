# By Allan Saddi
import select
import struct
import socket
import errno

__all__ = ['FCGIApp']

# Constants from the spec.
FCGI_LISTENSOCK_FILENO = 0

FCGI_HEADER_LEN = 8

FCGI_VERSION_1 = 1

FCGI_BEGIN_REQUEST = 1
FCGI_ABORT_REQUEST = 2
FCGI_END_REQUEST = 3
FCGI_PARAMS = 4
FCGI_STDIN = 5
FCGI_STDOUT = 6
FCGI_STDERR = 7
FCGI_DATA = 8
FCGI_GET_VALUES = 9
FCGI_GET_VALUES_RESULT = 10
FCGI_UNKNOWN_TYPE = 11
FCGI_MAXTYPE = FCGI_UNKNOWN_TYPE

FCGI_NULL_REQUEST_ID = 0

FCGI_KEEP_CONN = 1

FCGI_RESPONDER = 1
FCGI_AUTHORIZER = 2
FCGI_FILTER = 3

FCGI_REQUEST_COMPLETE = 0
FCGI_CANT_MPX_CONN = 1
FCGI_OVERLOADED = 2
FCGI_UNKNOWN_ROLE = 3

FCGI_MAX_CONNS = 'FCGI_MAX_CONNS'
FCGI_MAX_REQS = 'FCGI_MAX_REQS'
FCGI_MPXS_CONNS = 'FCGI_MPXS_CONNS'

FCGI_Header = '!BBHHBx'
FCGI_BeginRequestBody = '!HB5x'
FCGI_EndRequestBody = '!LB3x'
FCGI_UnknownTypeBody = '!B7x'

FCGI_BeginRequestBody_LEN = struct.calcsize(FCGI_BeginRequestBody)
FCGI_EndRequestBody_LEN = struct.calcsize(FCGI_EndRequestBody)
FCGI_UnknownTypeBody_LEN = struct.calcsize(FCGI_UnknownTypeBody)

if __debug__:
    import time

    # Set non-zero to write debug output to a file.
    DEBUG = 0
    DEBUGLOG = '/tmp/fcgi.log'

    def _debug(level, msg):
        if DEBUG < level:
            return

        try:
            f = open(DEBUGLOG, 'a')
            f.write('%sfcgi: %s\n' % (time.ctime()[4:-4], msg))
            f.close()
        except:
            pass

def decode_pair(s, pos=0):
    """
    Decodes a name/value pair.

    The number of bytes decoded as well as the name/value pair
    are returned.
    """
    nameLength = ord(s[pos])
    if nameLength & 128:
        nameLength = struct.unpack('!L', s[pos:pos+4])[0] & 0x7fffffff
        pos += 4
    else:
        pos += 1

    valueLength = ord(s[pos])
    if valueLength & 128:
        valueLength = struct.unpack('!L', s[pos:pos+4])[0] & 0x7fffffff
        pos += 4
    else:
        pos += 1

    name = s[pos:pos+nameLength]
    pos += nameLength
    value = s[pos:pos+valueLength]
    pos += valueLength

    return (pos, (name, value))

def encode_pair(name, value):
    """
    Encodes a name/value pair.

    The encoded string is returned.
    """
    nameLength = len(name)
    if nameLength < 128:
        s = chr(nameLength)
    else:
        s = struct.pack('!L', nameLength | 0x80000000L)

    valueLength = len(value)
    if valueLength < 128:
        s += chr(valueLength)
    else:
        s += struct.pack('!L', valueLength | 0x80000000L)

    return s + name + value

class Record(object):
    """
    A FastCGI Record.

    Used for encoding/decoding records.
    """
    def __init__(self, type=FCGI_UNKNOWN_TYPE, requestId=FCGI_NULL_REQUEST_ID):
        self.version = FCGI_VERSION_1
        self.type = type
        self.requestId = requestId
        self.contentLength = 0
        self.paddingLength = 0
        self.contentData = ''

    def _recvall(sock, length):
        """
        Attempts to receive length bytes from a socket, blocking if necessary.
        (Socket may be blocking or non-blocking.)
        """
        dataList = []
        recvLen = 0
        while length:
            try:
                data = sock.recv(length)
            except socket.error, e:
                if e[0] == errno.EAGAIN:
                    select.select([sock], [], [])
                    continue
                else:
                    raise
            if not data: # EOF
                break
            dataList.append(data)
            dataLen = len(data)
            recvLen += dataLen
            length -= dataLen
        return ''.join(dataList), recvLen
    _recvall = staticmethod(_recvall)

    def read(self, sock):
        """Read and decode a Record from a socket."""
        try:
            header, length = self._recvall(sock, FCGI_HEADER_LEN)
        except:
            raise EOFError

        if length < FCGI_HEADER_LEN:
            raise EOFError
        
        self.version, self.type, self.requestId, self.contentLength, \
                      self.paddingLength = struct.unpack(FCGI_Header, header)

        if __debug__: _debug(9, 'read: fd = %d, type = %d, requestId = %d, '
                             'contentLength = %d' %
                             (sock.fileno(), self.type, self.requestId,
                              self.contentLength))
        
        if self.contentLength:
            try:
                self.contentData, length = self._recvall(sock,
                                                         self.contentLength)
            except:
                raise EOFError

            if length < self.contentLength:
                raise EOFError

        if self.paddingLength:
            try:
                self._recvall(sock, self.paddingLength)
            except:
                raise EOFError

    def _sendall(sock, data):
        """
        Writes data to a socket and does not return until all the data is sent.
        """
        length = len(data)
        while length:
            try:
                sent = sock.send(data)
            except socket.error, e:
                if e[0] == errno.EAGAIN:
                    select.select([], [sock], [])
                    continue
                else:
                    raise
            data = data[sent:]
            length -= sent
    _sendall = staticmethod(_sendall)

    def write(self, sock):
        """Encode and write a Record to a socket."""
        self.paddingLength = -self.contentLength & 7

        if __debug__: _debug(9, 'write: fd = %d, type = %d, requestId = %d, '
                             'contentLength = %d' %
                             (sock.fileno(), self.type, self.requestId,
                              self.contentLength))

        header = struct.pack(FCGI_Header, self.version, self.type,
                             self.requestId, self.contentLength,
                             self.paddingLength)
        self._sendall(sock, header)
        if self.contentLength:
            self._sendall(sock, self.contentData)
        if self.paddingLength:
            self._sendall(sock, '\x00'*self.paddingLength)

def _fcgiGetValues(sock, vars):
    # Construct FCGI_GET_VALUES record
    outrec = Record(FCGI_GET_VALUES)
    data = []
    for name in vars:
        data.append(encode_pair(name, ''))
    data = ''.join(data)
    outrec.contentData = data
    outrec.contentLength = len(data)
    outrec.write(sock)

    inrec = Record()
    inrec.read(sock)
    result = {}
    if inrec.type == FCGI_GET_VALUES_RESULT:
        pos = 0
        while pos < inrec.contentLength:
            pos, (name, value) = decode_pair(inrec.contentData, pos)
            result[name] = value
    return result

def _fcgiParams(sock, requestId, params):
    rec = Record(FCGI_PARAMS, requestId)
    data = []
    for name,value in params.items():
        data.append(encode_pair(name, value))
    data = ''.join(data)
    rec.contentData = data
    rec.contentLength = len(data)
    rec.write(sock)

_environPrefixes = ['SERVER_', 'HTTP_', 'REQUEST_', 'REMOTE_', 'PATH_',
                    'CONTENT_']
_environCopies = ['SCRIPT_NAME', 'QUERY_STRING', 'AUTH_TYPE']
_environRenames = {}

def _filterEnviron(environ):
    result = {}
    for n in environ.keys():
        for p in _environPrefixes:
            if n.startswith(p):
                result[n] = environ[n]
        for c in _environCopies:
            if n == c:
                result[n] = environ[n]
        for oldname,newname in _environRenames.items():
            if n == oldname:
                result[newname] = environ[n]
    return result

def _lightFilterEnviron(environ):
    result = {}
    for n in environ.keys():
        if n.upper() == n:
            result[n] = environ[n]
    return result

class FCGIApp(object):
    def _getConnection(self):
        if self.connect is not None:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(self.connect)
            return sock

    def __init__(self, command=None, connect=None, host=None, port=None, filterEnviron=True):
        if host is not None:
            assert port is not None
            connect=(host, port)

        assert (command is not None and connect is None) or \
               (command is None and connect is not None)

        self.command = command
        self.connect = connect

        self.filterEnviron = filterEnviron

        #sock = self._getConnection()
        #print _fcgiGetValues(sock, ['FCGI_MAX_CONNS', 'FCGI_MAX_REQS', 'FCGI_MPXS_CONNS'])
        #sock.close()
        
    def __call__(self, environ, start_response):
        #print environ
        
        sock = self._getConnection()

        rec = Record(FCGI_BEGIN_REQUEST, 1)
        rec.contentData = struct.pack(FCGI_BeginRequestBody, FCGI_RESPONDER, 0)
        rec.contentLength = FCGI_BeginRequestBody_LEN
        rec.write(sock)

        if self.filterEnviron:
            params = _filterEnviron(environ)
        else:
            params = _lightFilterEnviron(environ)
        #print params
        _fcgiParams(sock, 1, params)
        _fcgiParams(sock, 1, {})

        while True:
            s = environ['wsgi.input'].read(4096)
            rec = Record(FCGI_STDIN, 1)
            rec.contentData = s
            rec.contentLength = len(s)
            rec.write(sock)

            if not s: break
            
        rec = Record(FCGI_DATA, 1)
        rec.write(sock)

        result = []
        while True:
            inrec = Record()
            inrec.read(sock)
            if inrec.type == FCGI_STDOUT:
                if inrec.contentData:
                    result.append(inrec.contentData)
            elif inrec.type == FCGI_STDERR:
                environ['wsgi.errors'].write(inrec.contentData)
            elif inrec.type == FCGI_END_REQUEST:
                break
            
        sock.close()

        result = ''.join(result)

        # Parse response headers
        status = '200 OK'
        headers = []
        pos = 0
        while True:
            eolpos = result.find('\n', pos)
            if eolpos < 0: break
            line = result[pos:eolpos-1]
            pos = eolpos + 1

            line = line.strip()
            if not line: break

            header, value = line.split(':')
            header = header.strip().lower()
            value = value.strip()

            if header == 'status':
                status = value
                if status.find(' ') < 0:
                    status += ' FCGIApp'
            else:
                headers.append((header, value))

        result = result[pos:]
        
        #print headers
        #print len(result)
        
        start_response(status, headers)
        return [result]

if __name__ == '__main__':
    from flup.server.ajp import WSGIServer
    app = FCGIApp(connect=('localhost', 4242))
    WSGIServer(app).run()
