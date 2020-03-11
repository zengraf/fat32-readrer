class Path:
    def __init__(self, path='/'):
        if path == '/':
            self.directories = list()
        else:
            self.directories = path.replace(r'\ ', ' ').split('/')

    def go_into(self, path):
        if path[0] == '/':
            self.directories = list()

        directories = path.replace(r'\ ', ' ').split('/')
        for d in directories:
            if d == '.' or d == '':
                continue
            elif d == '..':
                self.up()
            else:
                self.directories.append(d)

    def up(self):
        self.directories.pop()

    def to_string(self):
        return "/" + "/".join(self.directories)
