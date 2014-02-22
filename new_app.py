from flask import Flask, render_template, url_for
from TaskCLI import TaskCLI
from collections import namedtuple
import thread
import traceback
import utils

log = utils.get_logger(name=__name__)
CLI_NUM = 0
app = Flask(__name__)

@app.route("/")
def home_page():
    urls = get_urls()
    log.debug("Found following URLS: %s", "\n".join([url[1] for url in urls]))
    return render_template("home.html", urls=urls)

@app.route("/tasks")
def tasks():   
    log.debug("Loading /tasks")
    headers        = ("Task", "Date", "Start", "Stop", "Total", "Status") 
    entry          = namedtuple("Entry", headers)
    tables_entries = {}
    for task in cli.get_tasks(parent="None"):
        entries = []
        log.debug("Found task: %s", task.get_name())
        sub_tasks = get_sub_tasks(task)
        log.debug("Found subtasks: %s", ", ".join([t.get_name() for t in 
                                                   sub_tasks]))
        sub_tasks.append(task)
        sub_tasks.sort(key=lambda task: task.get_name())
        total_time = 0
        for sub_task in sub_tasks:
            for timer in sub_task.get_timers():

                date, start = timer.start_time()
                dummy, stop = timer.stop_time()
                time_secs   = timer.total_time().total_seconds()
                time_str    = format_seconds(time_secs)
                status      = timer.get_status()

                entries.append(entry(Task=sub_task.get_name().strip(
                                            task.get_name()),
                                     Date=date,
                                     Start=start,
                                     Stop=stop,
                                     Total=time_str,
                                     Status=status))

                if sub_task.get_name() == task.get_name():
                    if time_secs:
                        total_time += time_secs

        # Add a summary to the end.
        entries.append(entry(Task="Summary",
                             Date="",
                             Start="",
                             Stop="",
                             Total=format_seconds(total_time),
                             Status=task.get_status()))

        tables_entries[task.get_name()] = entries 
        log.debug("%s entry(s) for task", len(entries))
        log.debug("\n%s", "\n".join([e.Task for e in entries]))

    log.debug("Generating tables: %s", ", ".join(tables_entries))
    return render_template("tasks.html",
                           headers=headers,
                           tables_entries=tables_entries)

def get_urls():
    links = []
    print app.url_map
    for rule in app.url_map.iter_rules():
        try: 
            links.append((rule.endpoint, url_for(rule.endpoint)))
        except Exception:
            log.error(traceback.format_exc())

    return links

def get_sub_tasks(task):
    sub_tasks = cli.get_tasks(parent=task)
    for sub_task in sub_tasks:
        sub_tasks.extend(get_sub_tasks(sub_task))
    return sub_tasks

def format_seconds(total):
    hours = int(total)/(60*60)
    mins  = (int(total)/60)%60
    return "%dh%02dm" % (hours, mins)  

if __name__ == "__main__":
    
    # Create the CLI and start it.
    cli = TaskCLI()
    thread.start_new_thread(cli.cmdloop, ("test",))
    
    # Run the app. Will block here until App exists.
    app.run(debug=True)
    #app.run()

    # If the App is reloaded kill the existing CLI
    cli.do_exit(0)
