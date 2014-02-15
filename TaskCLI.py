import cmd
import time
import datetime
import textwrap
import pickle
import os
import sys
import thread


class TaskCLI(cmd.Cmd):
    """CLI that can be used to carry out simple operations."""
    def __init__(self, tasks={}):
        # Initiate the base class.
        cmd.Cmd.__init__(self)
        # Overwrite the prompt with a custom version.
        self._set_new_prompt(text="")

        # Name of the object
        self._name = ""

        # Dictionary for storing Tasks.
        self._tasks = tasks

        # The current task
        self._current_task = None

        # Wrapper for formatting long strings
        self._wrapper = self._get_wrapper()

        # Get the logfile.
        self._logfile = self._get_logfile()
        self._log("Started TaskCLI")

        # Create the object that contains the shortcuts.
        self._shortcut = Shortcut()

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
        self._log(line)

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
            task_name = "-".join([self._current_task.get_name(), task])
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
        if self._current_task != task.get_parent():
            self._to_screen("Unable to start this task Either another task is "
                            "already running, this task has a parent task "
                            "which hasn't been started yet or this task is "
                            "already running.")
        else:
            task.start()
            self._set_new_prompt(text=task.get_name())
            self._current_task = task
            self._log("Started Task: %s" % self._current_task.get_name())
            
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
            self._log("Stopped Task: %s" % self._current_task.get_name())
        except:
            self._to_screen("No tasks currently running.")
            return

        self._current_task = self._current_task.get_parent()
        try:
            self._set_new_prompt(text=self._current_task.get_name())
        except:
            self._set_new_prompt(text="")

    def help_stoptask(self):
        description = ("Stop's the current running task. If the task had a "
                       "parent it drops back down to the parent.")
        arguments = {}
        self._help_text(description=description,
                        arguments=arguments)        

    #def do_EOF(self, line):
    #    return True

    def do_exit(self, line):
        """do_exit

        Purpose: Called to exit the Base CLI and pickle the current tasks so
                 that we don't lose the data.

        Returns: Nothing
        """
        # Stop all running tasks and return the CLI to the start before saving.
        for task in self._get_running_tasks():
            task.stop()
        self._current_task = None
        self._set_new_prompt(text="")

        self._log("Exiting TaskCLI")
        self._log("\n" + self.do_times("", user_called=False))

        # Use the date as the filename.
        filename = datetime.datetime.fromtimestamp(
            time.time()).strftime("%d-%m-%Y.p")

        # Save off the BaseCLI and subsequently all child objects.
        pickle.dump(self, open(filename, "wb"))
        
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
            task_times[task.get_name()] = self._format_timers(task)

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
            print task.get_name() 

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
        title    = "Task: %s" % task.get_name()
        headers  = "DATE\t\t START\t STOP\t TOTAL\t STATUS"
        template = "%s\t %s\t %s\t %s\t %s"
        footer   = "TOTAL:\t\t \t \t %s\t %s"        
        task_times = []
        task_times.append(title)
        task_times.append(headers)
        total_status = task.status()
        total_time = 0
        for timer in task._timers:
            date, start = timer.start_time()
            dummy, stop = timer.stop_time()
            time_secs   = timer.total_time().total_seconds()
            time_str    = self._format_seconds(time_secs)
            status      = timer.status()

            line = template % (date, start, stop, time_str, status)
            task_times.append(line)

            if time_secs:
                total_time += time_secs

        final_line = footer % (self._format_seconds(total_time), total_status)
        task_times.append(final_line)

        return task_times

    def _format_seconds(self, total):
        """_format_seconds
        """
        hours = int(total)/(60*60)
        mins  = (int(total)/60)%60
        return "%dh%02dm" % (hours, mins)  
    
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

    def _get_running_tasks(self):
        return [task for task in self._tasks.values() 
                if task.status() == "Running"]

    def _get_logfile(self):
        filename = datetime.datetime.fromtimestamp(
            time.time()).strftime("cli_logs-%d-%m-%Y.txt")
        return open(filename, "a")

    def _log(self, message):
        timestamp = datetime.datetime.fromtimestamp(
            time.time()).strftime("%H:%M:%S")
        self._logfile.write("\n[%s] %s" % (timestamp, message)) 

class Task():
    """The Task CLI used when Tasks are created."""
    def __init__(self, name, parent):
        self._name = name
        self._timers = []
        self._timer = None
        self._parent = parent
        self._status = "Stopped"

    def get_name(self):
        """Getter for the Tasks name."""
        return self._name

    def get_parent(self):
        """Getter for the Tasks parent."""
        return self._parent

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

    def status(self):
        """Returns the status of the task, either "Running" or "Stopped"."""
        return self._status

class Timer():
    """Class for timing things."""
    def __init__(self):
        self._start_time = None
        self._stop_time = None
        self._status = None
        self.total_time
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

    def status(self):
        """Returns the staus of the current timer.

        Returns: The current status: "Stopped" OR "Running"
        """
        return self._status


class Shortcut():
    def __init__(self):
        self._const = {
            "ssh": (self._ssh, "tool for sshing"),
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

    def _summary(self):
        summary = ""
        for sc in self._const:
            summary += " %s:\t%s\n" % (sc, self._const[sc][1])
        return summary

    def _parse_input(self, text):
        return text.split()[0], text.split()[1:]


if __name__ == '__main__':

    filename = datetime.datetime.fromtimestamp(
        time.time()).strftime("%d-%m-%Y.p")
    if os.path.isfile(filename):
    #    tasks = pickle.load(open(filename, "rb"))
        msg = "Welcome to the TaskCLI, Loaded previous data."
        cli = pickle.load(open(filename, "rb"))
    else:
    #    tasks = {}
        msg = "Welcome to TaskCLI, no data to load."
        cli = TaskCLI()

    cli.cmdloop(msg)