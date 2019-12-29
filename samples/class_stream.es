


class Node(Proc.TextNode) {

    execute(self, stream) => {
        count = 0
        while (line = stream.stdin.readline2()) {
            if (count++ > 10) {
                break
            }
            stream.stdout.writeline2(line.upper());
        }
    }
}

print(Node())

exec cat README.md |> Node()