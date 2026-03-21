import io

"""
    A custom class inheriting from io.RawIOBase — the base class for
    raw (unbuffered) binary I/O.
    This is needed because io.BufferedReader requires a
    RawIOBase object to wrap.

"""
class ProgressReader(io.RawIOBase):

    def __init__(self, fobj, progress):
        """
        Store the raw file object (fobj)
        and the tqdm progress bar (progress)
        as instance variables.
        """

        self.fobj = fobj
        self.progress = progress

    def readable(self):
        """
        io.RawIOBase.readable() returns False by default.
        io.BufferedReader checks this before doing anything
        and raises UnsupportedOperation if it is False.
        Overriding it to return True tells BufferedReader
        the stream is readable
        """
        return True

    def readinto(self, b):
        """
        The core method io.BufferedReader calls internally. It:
        * Reads up to len(b) bytes from the raw file into the pre-allocated buffer b
        * Gets back n, the number of bytes actually read
        * Updates the tqdm bar by n bytes
        * Returns n so BufferedReader knows how many bytes were filled
        """
        n = self.fobj.readinto(b)
        if n:
            self.progress.update(n)
        return n