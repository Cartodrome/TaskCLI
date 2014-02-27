from flask import Flask, render_template, url_for
from TaskCLI import TaskCLI, format_seconds, get_sub_tasks
from collections import namedtuple
import thread
import traceback
import utils
import os
import argparse

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
        log.debug("Found task: %s", task.name)
        sub_tasks = get_sub_tasks(task)
        log.debug("Found subtasks: %s", ", ".join([t.name for t in sub_tasks]))
        sub_tasks.append(task)
        sub_tasks.sort(key=lambda task: task.name)
        total_time = 0
        for sub_task in sub_tasks:
            for timer in sub_task.timers:

                date, start = timer.start_time()
                dummy, stop = timer.stop_time()
                time_secs   = timer.total_time().total_seconds()
                time_str    = format_seconds(time_secs)
                status      = timer.get_status()

                entries.append(entry(Task=sub_task.name.lstrip(
                                                        task.name.lstrip("-")),
                                     Date=date,
                                     Start=start,
                                     Stop=stop,
                                     Total=time_str,
                                     Status=status))

                if sub_task.name == task.name:
                    if time_secs:
                        total_time += time_secs

        # Add a summary to the end.
        entries.append(entry(Task="Summary",
                             Date="",
                             Start="",
                             Stop="",
                             Total=format_seconds(total_time),
                             Status=task.status))

        tables_entries[task.name] = entries 
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

def get_args():
    parser = argparse.ArgumentParser(description="TaskCLI WebServer")
    parser.add_argument('mode', metavar='<mode>', type=str, 
        help="Either - 'DEV' (to run as a development server), 'LIVE' (to run "
             "the Live server), 'UNIT' (to run unit tests).")
    parser.add_argument('--noreload', action='store_true',
        help="stop the development server from autoreloading")
    
    args = parser.parse_args()

    if args.mode in ["UNIT", "DEV", "LIVE"]:
        pass
    else:
        parser.print_usage()
        quit()

    return args

def start_unit_tests():
    pass

def start_live_server():
    cli = TaskCLI()
    thread.start_new_thread(cli.cmdloop, ("Welcome to TaskCLI",))
    app.run()

def start_dev_server(use_reloader=True):
    # If we're not careful here the Werkzeug reloader will created multiple
    # instances of the TaskCLI object resulting in some funky behaviour. More
    # details here: http://stackoverflow.com/questions/11571656
    if use_reloader and not os.environ.get("WERKZEUG_RUN_MAIN"):
        log.info('startup: pid %d is the werkzeug reloader', os.getpid())
    else:
        log.info('startup: pid %d is the active werkzeug', os.getpid())
        cli = TaskCLI()
        thread.start_new_thread(cli.cmdloop, ("Development CLI",))

    app.run(debug=True, use_reloader=use_reloader)


if __name__ == "__main__":

    args = get_args()

    if args.mode == "UNIT":
        start_unit_tests()
    elif args.mode == "DEV":
        start_dev_server(use_reloader=(not args.noreload))
    elif args.mode == "LIVE":
        start_live_server()
    else:
        AssertionError("Webserver failed to start.")
