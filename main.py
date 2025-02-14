import sys
import os
import subprocess
import shlex
from io import StringIO
import re

class Redirect:
    def __init__(self, stdout=None, stderr=None):
        self.stdout = stdout
        self.stderr = stderr
        self._old_stdout = sys.stdout
        self._old_stderr = sys.stderr

    def __enter__(self):
        if self.stdout:
            sys.stdout = self.stdout
        if self.stderr:
            sys.stderr = self.stderr

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self._old_stdout
        sys.stderr = self._old_stderr

def echo(args):
    return ' '.join(args) + '\n'

def find_in_path(param):
    for directory in os.environ["PATH"].split(os.pathsep):
        potential_path = os.path.join(directory, param)
        if os.path.isfile(potential_path) and os.access(potential_path, os.X_OK):
            return potential_path
    return None

def current_working_dir():
    return os.getcwd()

def change_working_dir(directory):
    try:
        os.chdir(os.path.expanduser(directory))
        return ""
    except Exception as e:
        return f"cd: {directory}: {str(e)}\n"

def redirect_output(cmd_line):
    tokens = shlex.split(cmd_line)
    redir_index = -1
    redir_token = None
    
    # Identifica o operador de redirecionamento
    for i, token in enumerate(tokens):
        if re.fullmatch(r'\d*>>?', token):
            redir_index = i
            redir_token = token
            break
            
    if redir_index == -1:
        return

    # Parsing do operador
    fd = 1
    operator = redir_token
    if not redir_token.startswith('>'):
        fd_part = re.match(r'^\d+', redir_token)
        if fd_part:
            fd = int(fd_part.group())
            operator = redir_token[fd_part.span()[1]:]

    mode = 'w' if operator in ('>', '1>', '2>') else 'a'
    file_name = tokens[redir_index + 1]
    command_part = tokens[:redir_index]

    # Comandos internos (echo, pwd, type, cd)
    builtins = ['echo', 'pwd', 'type', 'cd']
    if command_part and command_part[0] in builtins:
        stdout_buffer = StringIO()
        stderr_buffer = StringIO()
        
        with Redirect(stdout=stdout_buffer, stderr=stderr_buffer):
            try:
                match command_part:
                    case ["pwd"]:
                        print(current_working_dir())
                    case ["echo", *args]:
                        sys.stdout.write(echo(args))
                    case ["type", cmd]:
                        if cmd in ['echo', 'pwd', 'type', 'cd']:
                            print(f"{cmd} is a shell builtin")
                        else:
                            path = find_in_path(cmd)
                            print(f"{cmd} is {path}" if path else f"{cmd} not found")
                    case ["cd", *args]:
                        dir_path = ' '.join(args) if args else "~"
                        error = change_working_dir(dir_path)
                        if error:
                            sys.stderr.write(error)
            except Exception as e:
                sys.stderr.write(f"Error: {str(e)}\n")
                
        # Escrita no arquivo conforme fd
        with open(file_name, mode) as f:
            output = stderr_buffer.getvalue() if fd == 2 else stdout_buffer.getvalue()
            f.write(output)

    # Comandos externos (ls, cat, etc)
    else:
        try:
            with open(file_name, mode) as f:
                if fd == 1:
                    subprocess.run(command_part, stdout=f, stderr=subprocess.PIPE)
                elif fd == 2:
                    subprocess.run(command_part, stderr=f, stdout=subprocess.PIPE)
                else:
                    subprocess.run(command_part, stdout=f, stderr=subprocess.PIPE)
        except FileNotFoundError:
            print(f"{command_part[0]}: command not found")

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    while True:
        sys.stdout.write("$ ")
        sys.stdout.flush()
        command = input().strip()
        
        if not command:
            continue
            
        # Verifica se há redirecionamento
        if any(re.match(r'\d*>>?', token) for token in shlex.split(command)):
            redirect_output(command)
            continue
            
        tokens = shlex.split(command)
        match tokens:
            case ["clear"]:
                clear()
            case ["cd", *args]:
                error = change_working_dir(' '.join(args))
                if error:
                    sys.stderr.write(error)
            case ["pwd"]:
                print(current_working_dir())
            case ["echo", *args]:
                sys.stdout.write(echo(args))
            case ["type", cmd]:
                if cmd in ['echo', 'pwd', 'type', 'cd']:
                    print(f"{cmd} is a shell builtin")
                else:
                    path = find_in_path(cmd)
                    print(f"{cmd} is {path}" if path else f"{cmd} not found")
            case _:
                if not tokens:
                    continue
                exe = find_in_path(tokens[0])
                if exe:
                    subprocess.run(tokens)
                else:
                    print(f"{tokens[0]}: command not found")

if __name__ == "__main__":
    main()