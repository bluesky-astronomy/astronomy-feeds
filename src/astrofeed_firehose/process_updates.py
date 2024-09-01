class ProcessUpdate:
    """Base class for any update to be sent between processes."""

    pass


class NewPostUpdate(ProcessUpdate):
    """Notify that a new post has been added and needs to be communicated to all
    other subprocesses so that post liking and deletion can keep working.
    """

    def __init__(self, uri):
        self.uri = uri


class ExistingPostsUpdate(ProcessUpdate):
    """Sent from manager to subprocess, this updates the subprocess on the current list
    of posts that it should check when processing likes and deletions.
    """

    def __init__(self, posts):
        self.posts = posts


class ValidAccountsUpdate(ProcessUpdate):
    """Sent from manager to subprocess, this updates the subprocess on the current list
    of accounts that are authorized to post to the Astronomy feeds and should be
    tracked.
    """

    def __init__(self, accounts):
        self.accounts = accounts