import cmd
import time
import datetime
import textwrap

class TaskCLI(cmd.Cmd):
    """CLI that can be used to carry out simple operations."""
    def __init__(self, cli_level=0):
        # Initiate the base class.
        cmd.Cmd.__init__(self)
        # Overwrite the prompt with a custom version.
        self._set_new_prompt(text="")

        # Name of the object
        self._name = ""

        # Dictionary for storing Tasks.
        self._tasks = {}

        # Wrapper for formatting long strings
        self._wrapper = textwrap.TextWrapper(width=50)

        # How nested are we in the CLI
        self._cli_level = cli_level

    def do_addtask(self, task):
        """do_addtask

        Purpose: Creates a new Task that time can be tracked against and
                 notes added to.

        Params:  task - The name of the Task. 

        Returns: Nothing.
        """
        if task in self._tasks:
            print ("Task already exists, please choose another name.\n"
                   "Current tasks are:\n  %s" % 
                   "\n  ".join(self._tasks))
        else:
            name = "%s-%s" % (self._name, task) 
            new_task = Task(name=name,cli_level=self._cli_level + 1)
            self._tasks[task] = new_task
            print "Created new task of name: %s" % task

    def help_addtask(self):
        """help_addtask

        Purpose: Print the help text for addtask when called with:
                   help addtask.
        """
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
        if task not in self._tasks:
            print ("No Task exists of that name. Current tasks are:"
                   "\n  %s" % "\n  ".join(self._tasks))
        else:
            self._tasks[task].start()
            self._switch_cli(new_cli=self._tasks[task])
            
    def help_starttask(self):
        """help_addtask

        Purpose: Print the help text for starttask when called with:
                   help starttask.
        """
        description = ("Starts an existing task. Once the task is "
                       "started notes can be made against it and the "
                       "time spent on the task is tracked.")
        arguments = {"task" : "The name of the task to start."}
        self._help_text(description=description,
                        arguments=arguments)

    def complete_starttask(self, text, line, begidx, endidx):
        """complete_starttask

        Purpose: Provides autocomplete functionality for teh starttask
                 command.
        """
        if not text:
            completions = self._tasks.keys()
        else:
            completions = [t for t in self._tasks if 
                           t.startswith(text)]
        return completions

    def do_EOF(self, line):
        return True

    def do_exit(self, line):
        """do_exit

        Purpose: Called to exit the current CLI.
        """
        try:
            self.stop()
        except:
            pass
        return True

    def help_exit(self):
        """help_exit

        Pupose: Prints the help text for do_exit when help exit is
                called.
        """
        description = ("This exits the current task. The Timer for the "
                       "task will also be stopped. If this is the base "
                       "level of the CLI then the python will exit.")
        arguments = {}
        self._help_text(description=description,
                        arguments=arguments)        

    def do_times(self, line, called=True):
        """do_times

        Purpose: Prints the times for all tasks below this object.

        Params: None.

        Returns: None.
        """
        task_times = {}
        # Get they times for all sub tasks.
        for task in self._tasks.values():
            task_times.update(task.do_times(line, called=False))

        # The base cli level doesn't have any tasks.
        if self._cli_level > 0:
            task_times.update(self._format_timers())

        # If this is where the CLI called the function print the
        # results.
        if called:
            for task, details in sorted(task_times.items(), 
                                        key=lambda x: x[1]):
                for detail in details:
                    print detail
                print ""
        else:
            return task_times

    def help_times(self):
        """help_times

        Purpose: Prints the helo text for do_times when help times is
                 called. 
        """
        description = "Prints the times for this task and all subtasks." 
        arguments = {}
        self._help_text(arguments=arguments,
                        description=description)

    def _format_timers(self):
        """_format_timers
        """
        task_times = {}
        title    = "Task: %s" % self.get_name()
        headers  = "DATE\t\t START\t STOP\t TOTAL\t STATUS"
        template = "%s\t %s\t %s\t %s\t %s"
        footer   = "TOTAL:\t\t \t \t %s\t %s"        
        task_times[self._name] = []
        task_times[self._name].append(title)
        task_times[self._name].append(headers)
        total_status = "Stopped"
        total_time = 0
        for timer in self._timers:
            date, start = timer.start_time()
            dummy, stop = timer.stop_time()
            time_secs   = timer.total_time().total_seconds()
            time_str    = self._format_seconds(time_secs)
            status      = timer.status()

            line = template % (date, start, stop, time_str, status)
            task_times[self._name].append(line)

            if status == "Running":
                total_status = "Running"
            if time_secs:
                total_time += time_secs

        final_line = footer % (self._format_seconds(total_time), total_status)
        task_times[self._name].append(final_line)

        return task_times

    def _format_seconds(self, total):
        """_format_seconds
        """
        hours = int(total)/(60*60)
        mins  = (int(total)/60)%60
        return "%dh%02dm" % (hours, mins)  

    def _switch_cli(self, new_cli):
        """_switch_cli

        Purpose: Changes the cli level that the user is using.

        Params:  new_cli - The TaskCLI object we are changing to.
        """
        new_cli.cmdloop("Entered new task: %s" % new_cli.get_name())
    
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

class BaseCLI(TaskCLI):
    """The Base CLI Object called by main"""
    def __init__(self):
        # Initiate the base class.
        TaskCLI.__init__(self)

class Task(TaskCLI):
    """The Task CLI used when Tasks are created."""
    def __init__(self, name, cli_level):
        # Initiate the base class.
        TaskCLI.__init__(self, cli_level=cli_level)

        self._name = name
        self._timers = []
        self._timer = None

        self._set_new_prompt(text=self._name)

    def get_name(self):
        """Getter for the Tasks name."""
        return self._name

    def start(self):
        """Called to start the task. Kicks off a Timer."""
        if not self._timer:
            self._timer = Timer()
            self._timers.append(self._timer)
        else:
            print "Warning: Task %s already started!" % self._name

    def stop(self):
        """Called to stop the Task and to stop the Timer and archive it."""
        try:
            self._timer.stop()
            self._timer = None
        except:
            print "Warning: Task %s was not timing!" % self._name

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

    def status(self):
        """Returns the staus of the current timer.

        Returns: The current status: "Stopped" OR "Running"
        """
        return self._status

if __name__ == '__main__':
    BaseCLI().cmdloop("Welcome to Sam's CLI")