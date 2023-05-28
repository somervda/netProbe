from microWebCli import MicroWebCli
import utime
import gc


def webPage(target, match,  quiet=True):
    gc.collect()
    timestamp = utime.ticks_us()
    not quiet and print("webPage start")
    wCli = MicroWebCli(target)
    not quiet and print('GET %s' % wCli.URL)
    try:
        wCli.OpenRequest()
        buf = memoryview(bytearray(1024))
        resp = wCli.GetResponse()
        matched = False
        if resp.IsSuccess():
            not quiet and print("webPage IsSuccess")
            # Only process first 1000 bytes
            if not resp.IsClosed():
                x = resp.ReadContentInto(buf)
                if x < len(buf):
                    buf = buf[:x]
                contentReadable = True
                try:
                    testStr = str(bytearray(buf), "utf-8")
                except:
                    contentReadable = False
                not quiet and print(str(bytearray(buf), "utf-8"))
                if contentReadable:
                    if match == "" or match in str(bytearray(buf), "utf-8"):
                        matched = True
                else:
                    # Cant do a match on zipped content
                    matched = False
            not quiet and print(
                'webPage GET success with "%s" content type' % resp.GetContentType())
        else:
            not quiet and print('webPage GET return %d code (%s)' %
                                (resp.GetStatusCode(), resp.GetStatusMessage()))
        t_elapsed = (utime.ticks_us()-timestamp) / 1000
        not quiet and print("elapsed:", t_elapsed)
        not quiet and print("matched:", matched)
        return t_elapsed, matched, resp.GetStatusCode()
    except:
        return None
