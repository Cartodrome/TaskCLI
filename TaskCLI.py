import cmd
import time
import datetime
import textwrap
import pickle
import os
import sys
import argparse
from thread import start_new_thread
try:
    import pyreadline
except:
    print ("Warning: Auto-completion won't work on Windows without the "
           "pyreadline module")


class TaskCLI(cmd.Cmd):
    """CLI that can be used to carry out simple operations."""
    def __init__(self):
        # Initiate the base class.
        cmd.Cmd.__init__(self)
        # Overwrite the prompt with a custom version.
        self._set_new_prompt(text="")

        self._tasks = {}
        self._current_task = None
        self.messages = []
        self.date = datetime.datetime.fromtimestamp(
                                              time.time()).strftime("%d-%m-%Y")

        # Wrapper for formatting long strings
        self._wrapper = self._get_wrapper()

        # Get the logfile.
        self._logfile = self._get_logfile()
        self._log("Started TaskCLI")

        # Create the object that contains the shortcuts.
        self._shortcut = Shortcut()

    def reset(self):
        # Save off the BaseCLI and subsequently all child objects.
        pickle.dump(self, open("%s.p" % self.date, "wb"))
        
        # Reset the class values now they've been saved off
        self._current_task = None
        self._tasks = {}
        self.messages = []
        self._set_new_prompt(text="")
        self.date = datetime.datetime.fromtimestamp(
                                              time.time()).strftime("%d-%m-%Y")
        self.__setstate__(self.__dict__)
        self._log("Reset TaskCLI")

    def __getstate__(self):
        self._log("Saving TaskCLI data")
        del self.__dict__["stdout"]
        del self.__dict__["stdin"]
        del self.__dict__["_wrapper"]
        del self.__dict__["_logfile"]
        del self.__dict__["_shortcut"]
        return self.__dict__

    def __setstate__(self, d):
        self.__dict__ = d
        self.__dict__["stdout"] = sys.stdout
        self.__dict__["stdin"] = sys.stdin
        self.__dict__["_wrapper"] = self._get_wrapper()
        self.__dict__["_logfile"] = self._get_logfile()
        self.__dict__["_shortcut"] = Shortcut()
        self._log("Restarting TaskCLI")

    def do_M(self, line):
        """do_M

        Purpose: Logs a line of text to the log file.

        Params:  line - The line of text to be logged.

        Returns: Nothing.
        """
        self.messages.append(self._log(line))

    def help_M(self):
        description = ("Logs a line of text to the output file.")
        arguments = {"line" : "The line to be logged to file"}
        self._help_text(description=description,
                        arguments=arguments)

    def do_SC(self, text):
        """do_SC

        Purpose: Takes a line of text and passes it to the Shortcut class. If
                 the text matches a shortcut in the class it will be executed.

        Returns: Nothing
        """
        try:
            print self._shortcut.run_cmd(text)
            self._log("SC: %s" % text)
        except:
            pass

    def help_SC(self):
        description = ("Pass text to SC to execute a shortcut")
        arguments = {"text" : "The text to be passed to SC"}
        self._help_text(description=description,
                        arguments=arguments)

    def do_addtask(self, task):
        """do_addtask

        Purpose: Creates a new Task that time can be tracked against and
                 notes added to.

        Params:  task - The name of the Task.

        Returns: Nothing.
        """
        if "-" in task:
            self._to_screen("Task names must not contain '-'")
            return

        try:
            task_name = "-".join([self._current_task.name, task])
        except:
            task_name = task

        if task_name in self._tasks:
            self._to_screen("Task already exists, please choose another name."
                            "\nCurrent tasks are:\n  %s" %
                            "\n  ".join(self._tasks))
            return
        else:
            new_task = Task(name=task_name,
                            parent=self._current_task)
            self._tasks[task_name] = new_task
            self._to_screen("Created new task of name: %s" % task_name)
            self._log("Added a new task: %s" % task_name)

    def help_addtask(self):
        description = ("Creates a new task. Once the task is started "
                       "notes can be made against it and the time "
                       "spent on the task is tracked. Tasks themselves "
                       "can have subtasks.")
        arguments = {"task" : "The name of the task, must be unique."}
        self._help_text(description=description,
                        arguments=arguments)

    def do_starttask(self, task):
        """do_starttask

        Purpose: Calls start on the Task and enters the task's CLI.

        Params:  task - The task that we want to start

        Returns: Noting.
        """
        try:
            task = self._tasks[task]
        except:
            self._to_screen("No Task exists of that name. Current tasks are:"
                            "\n  %s" % "\n  ".join(self._tasks))
            return

        # Check that the only running tasks are parents of this task.
        if self._current_task != task.parent:
            self._to_screen("Unable to start this task Either another task is "
                            "already running, this task has a parent task "
                            "which hasn't been started yet or this task is "
                            "already running.")
        else:
            task.start()
            self._set_new_prompt(text=task.name)
            self._current_task = task
            self._log("Started Task: %s" % self._current_task.name)

    def help_starttask(self):
        description = ("Starts an existing task. Once the task is "
                       "started notes can be made against it and the "
                       "time spent on the task is tracked.")
        arguments = {"task" : "The name of the task to start."}
        self._help_text(description=description,
                        arguments=arguments)

    def complete_starttask(self, text, line, begidx, endidx):
        """complete_starttask

        Purpose: Provides autocomplete functionality for the starttask
                 command.

        Return:  Nothing
        """
        if not text:
            completions = self._tasks.keys()
        else:
            completions = [t for t in self._tasks if
                           t.startswith(text)]
        return completions

    def do_stoptask(self, line):
        """do_stoptask

        Purpose: Stop the current running task.

        Returns: Nothing
        """
        try:
            self._current_task.stop()
            self._log("Stopped Task: %s" % self._current_task.name)
        except:
            self._to_screen("No tasks currently running.")
            return

        self._current_task = self._current_task.parent
        try:
            self._set_new_prompt(text=self._current_task.name)
        except:
            self._set_new_prompt(text="")

    def help_stoptask(self):
        description = ("Stop's the current running task. If the task had a "
                       "parent it drops back down to the parent.")
        arguments = {}
        self._help_text(description=description,
                        arguments=arguments)

    def emptyline(self):
        pass

    def do_EOF(self, line):
        self.do_exit(line)

    def do_exit(self, line):
        """do_exit

        Purpose: Called to exit the Base CLI and pickle the current tasks so
                 that we don't lose the data.

        Returns: Nothing
        """
        # Stop all running tasks and return the CLI to the start before saving.
        for task in self.get_tasks(status="Running"):
            task.stop()
        self._current_task = None
        self._set_new_prompt(text="")

        self._log("Exiting TaskCLI")
        self._log("\n" + self.do_times("", user_called=False))

        # Use the date as the filename.
        filename = "%s.p" % self.date

        # Save off the BaseCLI and subsequently all child objects.
        pickle.dump(self, open(filename, "wb"))

        print "Exiting"
        return True

    def help_exit(self):
        """help_exit

        Pupose: Prints the help text for do_exit when help exit is
                called.
        """
        description = ("This exits the CLI and saves off any data in a python "
                       "picklr file.")
        arguments = {}
        self._help_text(description=description,
                        arguments=arguments)

    def do_times(self, line, user_called=True):
        """do_times

        Purpose: Prints the times for all tasks below this object.

        Returns: The details printed to screen.
        """
        task_times = {}
        print_out = ""

        # Get they times for all sub tasks.
        for task in self._tasks.values():
            task_times[task.name] = self._format_timers(task)

        for task, details in sorted(task_times.items(),
                                    key=lambda x: x[1]):
            for detail in details:
                print_out += detail + "\n"
            print_out += "\n"

        if user_called:
            print print_out
        else:
            return print_out

    def help_times(self):
        description = "Prints the time spent on tasks."
        arguments = {}
        self._help_text(arguments=arguments,
                        description=description)

    def do_tasks(self, line):
        """do_tasks

        Purpose: Prints a list of all the current tasks.
        """
        for task in self._tasks.values():
            print task.name

    def help_tasks(self):
        description = "Prints a list of all tasks."
        arguments = {}
        self._help_text(arguments=arguments,
                        description=description)

    def help_help(self):
        description = ("Returns instructions on how to use a command. Can be "
                       "called with 'help' <command> or '?' <command>.")
        arguments = {"command": "The command you require help with"}
        self._help_text(arguments=arguments,
                        description=description)

    def _format_timers(self, task):
        """_format_timers
        """
        title    = "Task: %s" % task.name
        headers  = "DATE\t\t START\t STOP\t TOTAL\t STATUS"
        template = "%s\t %s\t %s\t %s\t %s"
        footer   = "TOTAL:\t\t \t \t %s\t %s"
        task_times = []
        task_times.append(title)
        task_times.append(headers)
        total_status = task.status
        total_time = 0
        for timer in task.timers:
            date, start = timer.start_time()
            dummy, stop = timer.stop_time()
            time_secs   = timer.total_time().total_seconds()
            time_str    = format_seconds(time_secs)
            status      = timer.status

            line = template % (date, start, stop, time_str, status)
            task_times.append(line)

            if time_secs:
                total_time += time_secs

        final_line = footer % (format_seconds(total_time), total_status)
        task_times.append(final_line)

        return task_times

    def _set_new_prompt(self, text=None):
        """ _set_new_prompt

        Purpose: Adds text to the pronpt that is displated to the user.

        Params:  text - The text to add to the prompt template.

        Returns: Nothing.
        """
        prompt_template = "SL %s#:"
        if text:
            self.prompt = prompt_template % text
        else:
            self.prompt = prompt_template % ""

    def _help_text(self, arguments={}, description=""):
        """_help_text

        Purpose: prints all help text in a generic format

        Params:  arguments - a Dictionary with the arguments as key and
                             a description of the argument as an entry.
                 description - a description of the function.

        Returns: None
        """
        print "\n".join(self._wrapper.wrap(description))
        if arguments:
            print ""
            print "Arguments:"
        for argument in arguments:
            text = " <%s> - %s" % (argument, arguments[argument])
            joiner = "\n      " + " " * len(argument)
            print joiner.join(self._wrapper.wrap(text))

    def _get_wrapper(self):
        return textwrap.TextWrapper(width=50)

    def _to_screen(self, message):
        for line in self._get_wrapper().wrap(message):
            print line

    def get_tasks(self,
                  status=None,
                  parent=None):
        filters = []

        if status:
            filters.append(lambda x: x.status == status)

        if parent:
            if parent == "None":
                filters.append(lambda x: x.parent == None)
            else:
                filters.append(lambda x: x.parent == parent)

        return self._apply_filters(self._tasks.values(), filters)

    def _apply_filters(self, list_to_be_filtered, list_of_filters):
        if not list_of_filters:
            return list_to_be_filtered
        else:
            return [elem for elem in list_to_be_filtered if False not in
                       [test(elem) for test in list_of_filters]]

    def _get_logfile(self):
        filename = "cli_logs-%s.txt" % self.date
        return open(filename, "a")

    def _log(self, message):
        timestamp = datetime.datetime.fromtimestamp(
            time.time()).strftime("%H:%M:%S")
        task_name = " " if not self._current_task else self._current_task.name
        line = (timestamp, task_name, message)
        self._logfile.write("\n[%s] [%s] %s" % line)
        return line


class Task():
    """The Task CLI used when Tasks are created."""
    def __init__(self, name, parent):
        self._name   = name
        self._timers = []
        self._timer  = None
        self._parent = parent
        self._status = "Stopped"

    def start(self):
        """Called to start the task. Kicks off a Timer."""
        if not self._timer:
            self._timer = Timer()
            self._timers.append(self._timer)
            self._status = "Running"
        else:
            print "Warning: Task %s already started!" % self._name

    def stop(self):
        """Called to stop the Task and to stop the Timer and archive it."""
        try:
            self._timer.stop()
            self._timer = None
            self._status = "Stopped"
        except:
            print "Warning: Task %s was not timing!" % self._name

    @property
    def name(self):
        """Getter for the Tasks name."""
        return self._name

    @property
    def parent(self):
        """Getter for the Tasks parent."""
        return self._parent

    @property
    def status(self):
        """Returns the status of the task, either "Running" or "Stopped"."""
        return self._status

    @property
    def timers(self):
        """Returns all the tasks Timers."""
        return self._timers


class Timer():
    """Class for timing things."""
    def __init__(self):
        self._start_time = None
        self._stop_time = None
        self._status = None
        self.start()

    def start(self):
        """Starts the timer."""
        self._start_time = datetime.datetime.fromtimestamp(time.time())
        self._status = "Running"

    def stop(self):
        """Stops the timer."""
        self._stop_time = datetime.datetime.fromtimestamp(time.time())
        self._status = "Stopped"

    def start_time(self):
        """ Returns the start time.

        Returns: as a tuple:
            date - date as a string: Mon DD-MM-YYYY
            time - time as a string: HH:MM
        """
        return self._start_time.strftime("%a %d-%m-%Y"), \
               self._start_time.strftime("%H:%M")

    def stop_time(self):
        """ Returns the stop time.

        Returns: as a tuple:
            date - date as a string: Mon DD-MM-YYYY
            time - time as a string: HH:MM
        """
        try:
            return self._stop_time.strftime("%a %d-%m-%Y"), \
                   self._stop_time.strftime("%H:%M")
        except:
            return None, None

    def total_time(self):
        """ Returns the difference between start and stop time.

        Returns: a datetime.timedelta object
        """
        try:
            return self._stop_time - self._start_time
        except:
            return datetime.datetime.fromtimestamp(time.time()) - \
                   self._start_time

    @property
    def status(self):
        """ Returns: The current status: "Stopped" OR "Running" """
        return self._status


class Shortcut():
    def __init__(self):
        self._const = {
            "ssh":       (self._ssh, "tool for sshing"),
            "unit_test": (self._unit_test, "unit testing utility")
        }

    def run_cmd(self, text):
        cmd, args = self._parse_input(text)

        try:
            func = self._const[cmd][0]
            return func(args)
        except:
            return ("Shortcut '%s' does not exist, shortcuts:\n%s" % (cmd,
                    self._summary()))

    def _ssh(self, args):
        print "ssh, %s" % args

    def _unit_test(self, args):
        return args

    def _summary(self):
        summary = ""
        for sc in self._const:
            summary += " %s:\t%s\n" % (sc, self._const[sc][1])
        return summary

    def _parse_input(self, text):
        return text.split()[0], text.split()[1:]

def format_seconds(seconds):
    """format_seconds

    Converts X number of seconds to a string of the format HhMMm (e.g 2h32m).

    Params:  seconds - The number of seconds.

    Returns: string of the formatted seconds.
    """
    hours = int(seconds)/(60*60)
    mins  = (int(seconds)/60)%60
    return "%dh%02dm" % (hours, mins)

def get_sub_tasks(cli, task):
    """get_sub_tasks

    Gets the sub_tasks of a given task.

    Params:  cli  - The TaskCLI object that contains the Task.
             task - The Task object.

    Returns: A list of child Tasks.
    """
    sub_tasks = cli.get_tasks(parent=task)
    for sub_task in sub_tasks:
        sub_tasks.extend(get_sub_tasks(cli, sub_task))
    return sub_tasks

def get_args():
    parser = argparse.ArgumentParser(description="TaskCLI")
    parser.add_argument('mode', metavar='<mode>', type=str,
        help="Either 'CLI' (to start tool) or 'UNIT' (to run unit tests).")

    args = parser.parse_args()

    if args.mode in ["UNIT", "CLI"]:
        pass
    else:
        parser.print_usage()
        quit()

    return args

def restart_at_midnight(cli):
    """Restarts the CLI at midnight"""
    sleep_time = (datetime.datetime.now().replace(hour=23,
                                                  minute=59,
                                                  second=59,
                                                  microsecond=999) -
                      datetime.datetime.now()).total_seconds()
    time.sleep(sleep_time)
    cli.reset()
    start_new_thread(restart_at_midnight, (cli,))

def start_cli(cli, msg="Welcome to TaskCLI"):
    start_new_thread(restart_at_midnight, (cli,))
    cli.cmdloop(msg)

def simulate_cmd(cli, cmd):
    l = cli.precmd(cmd)
    r = cli.onecmd(l)
    cli.postcmd(r, l)

def get_cli():
    filename = datetime.datetime.fromtimestamp(
        time.time()).strftime("%d-%m-%Y.p")
    user_input = None
    if os.path.isfile(filename):
        while 1:
            user_input = raw_input("Found previous data, load it? Y/N")
            if user_input in ["Y", "N"]:
                break
    if user_input == "Y":
        msg = "Welcome to the TaskCLI, Loaded previous data."
        cli = pickle.load(open(filename, "rb"))
    else:
        msg = "Welcome to TaskCLI, no data to load."
        cli = TaskCLI()
    return cli, msg

def run_unit_tests(cli=None):
    if not cli:
        print "Started Unit Tests\n"

        """ Test Shortcut """
        print " Testing Shortcut..."
        sc = Shortcut()
        # Test we pass arguments to a function
        result = sc.run_cmd("unit_test abc 123")
        assert result == ["abc", "123"]
        # Test we handle duff shortcuts
        result = sc.run_cmd("giberish sdf dg sdg ")
        assert type(result) is str
        print " ...Shortcut Passed.\n"

        """ Test Timer """
        print " Testing Timer..."
        t = Timer()
        # Check the timer is automatically started.
        assert t.status == "Running"
        t.stop()
        assert t.status == "Stopped"
        # Check the start and stop times returned.
        assert type(t.start_time()) is tuple
        assert type(t.start_time()[0]) is str and type(t.start_time()[1]) is str
        assert t.start_time() == t.stop_time()
        # Check the total seconds is a small number.
        seconds = t.total_time().total_seconds()
        assert seconds >= 0 and seconds <= 1
        print " ...Timer Passed.\n"

        """ Test Task """
        print " Testing Task..."
        # Test creation and initiation.
        parent  = Task(name="parent", parent=None)
        child1  = Task(name="child1", parent=parent)
        assert (child1.name == "child1" and child1.parent == parent and
                child1.status == "Stopped" and child1.timers == [])
        # Check start and stop behaviour is sensible.
        child1.stop()
        assert (child1.status == "Stopped" and child1.timers == [])
        for ii in range(2):
            child1.start()
            assert (child1.status == "Running" and len(child1.timers) == 1 and
                    type(child1.timers[0]) is type(Timer()))
        child1.stop()
        assert (child1.status == "Stopped" and len(child1.timers) == 1 and
                    type(child1.timers[0]) is type(Timer()))
        print " ...Task Passed.\n"

        """ Test TaskCLI """
        print " Testing TaskCLI..."
        cli = TaskCLI()
    else:
        print " Testing TaskCLI..."

    cli.help_help()
    cli.do_SC("dummy")
    cli.do_M("This is the first message.")
    cli.do_M("This is the last message.")
    cli.do_addtask("parent_task1")
    cli.do_addtask("parent_task2")
    cli.do_addtask("-")
    cli.do_starttask("parent_task1")
    cli.do_addtask("child_task1")
    cli.do_addtask("child_task2")
    cli.do_starttask("parent_task1-child_task1")
    cli.do_addtask("child_subtask")
    cli.do_starttask("parent_task1-child_task1-child_subtask")
    cli.do_stoptask("")
    cli.do_stoptask("")
    cli.do_starttask("parent_task1-child_task2")
    cli.do_stoptask("")
    cli.do_addtask("child_task3")
    cli.do_starttask("parent_task1-child_task3")
    cli.do_stoptask("")
    cli.do_stoptask("")
    cli.do_starttask("parent_task2")
    cli.do_stoptask("")
    cli.do_starttask("parent_task1")
    cli.do_stoptask("")
    cli.do_tasks("")
    cli.do_times("")
    cli.do_exit("")
    print " ...TaskCLI Passed.\n"
    print "All Tests Passed."

if __name__ == '__main__':

    args = get_args()

    if args.mode == "CLI":
        cli, msg = get_cli()
        start_cli(cli=cli, msg=msg)
    elif args.mode == "UNIT":
        run_unit_tests()
    else:
        AssertionError("TaskCLI failed to start.")
