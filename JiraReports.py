import jira
import datetime
import argparse

gU = ''
gP = ''
gServer = 'https://interactions.atlassian.net'
gUser_file = 'users.db'



def command_line():
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--user', required=True)
    parser.add_argument('-p', '--password', required=True)
    parser.add_argument('-m', '--missing', action='store_true', help='Print the missing work log report')
    parser.add_argument('-l', '--lift', action='store_true', help='Print the Lift work report')
    return parser.parse_args()


def get_users():
    return open(gUser_file).readlines()

def missing_time_report(interval):
    """
checks for time reporters who have not logged hours in the prior week

    """
    loggers = dict()

    # find the date range that interests us for this report
    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-4))).replace(hour=0, minute=0, second=0,
                                                                                           microsecond=0)  # Fix this to EDT for now
    wstart = today - datetime.timedelta(days=today.isoweekday() + interval)
    wend = wstart + datetime.timedelta(days=interval)

    jira_db = jira.JIRA(server=gServer, basic_auth=(gU, gP))

    ''' get the list of issues that have a worklog during the prior week'''
    issue_list = jira_db.search_issues(
        'worklogDate >= startOfWeek(-{0}d) AND worklogDate < startOfWeek()'.format(interval),
        maxResults=False)

    print("Date Range: {0}-{1}".format(wstart.strftime("%m/%d/%Y"), wend.strftime("%m/%d/%Y")))

    for issue in issue_list:
        # print("Processing issue {}".format(issue.key))
        worklogs = jira_db.worklogs(issue.key)
        for wlog in worklogs:
            started = datetime.datetime.strptime(wlog.started, "%Y-%m-%dT%H:%M:%S.%f%z")
            if wstart <= started < wend:
                name = wlog.author.displayName

                if name in loggers:
                    loggers[name] += wlog.timeSpentSeconds
                else:
                    loggers[name] = wlog.timeSpentSeconds

#    l = list(loggers.keys())
#    l.sort()
#    for name in l:
#        print("{0}: {1}".format(name, loggers[name] / 3600))

    user_list = [name.strip() for name in get_users()]

    print("\n--Missing--\n")
    for n in [name for name in user_list if name not in loggers.keys()]:
        print(n)

    print(
        'You have no time reported for the date range. Please enter your time as soon as possible. '
        'If you have been on vacation, please make a work log entry in CORPACT-8.'
    )


def jira_allocation_report():
    """
        Reports on all open tasks that have time remaining. This allows visualization across all projects of the
        work effort currently remaining
    :return: None
    """

    projects = dict()

    jira_db = jira.JIRA(server=gServer, basic_auth=(gU, gP))

    ''' get the list of issues that have a worklog during the prior week'''
    issue_list = jira_db.search_issues('remainingEstimate > 0 AND status != Closed',
                                       fields='summary, assignee, timeestimate, timeoriginalestimate, timespent, durdate, project',
                                       maxResults=False)

    for issue in issue_list:
        project = issue.fields.project.key
        if issue.fields.assignee is None:
            assignee = '--UNASSIGNED--'
        else:
            assignee = issue.fields.assignee.displayName
        if project in projects:
            if assignee in projects[project]['assignees']:
                projects[project]['assignees'][assignee]['issues'].append(issue)
            else:
                projects[project]['assignees'][assignee] = {'assignee': issue.fields.assignee, 'issues': [issue]}
        else:
            projects[project] = {'project': issue.fields.project}
            projects[project]['assignees'] = {assignee: {'assignee': issue.fields.assignee, 'issues': [issue]}}

    p_list = list(projects.keys())
    p_list.sort()
    for project in p_list:
        if project != 'CDFS':
            print(projects[project]['project'].name)
            a_list = list(projects[project]['assignees'].keys())
            a_list.sort()
            for assignee in a_list:
                i_list = projects[project]['assignees'][assignee]['issues']
                minutes = 0
                for issue in i_list:
                    minutes += issue.fields.timeestimate
                print("\t{}\t{}\t{:,.2f}".format(assignee, len(i_list), minutes/3600))


def lift_report(interval):
    """
    Find the total allocation to Lift by looking at all of the worklogs for LIFT and any issues that are linked to a
    LIFT issue

    :param interval:
    :return:
    """
    loggers = dict()

    # find the date range that interests us for this report
    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-4))).replace(hour=0, minute=0, second=0,
                                                                                           microsecond=0)  # Fix this to EDT for now
    wstart = today - datetime.timedelta(days=today.isoweekday() + interval)
    wend = wstart + datetime.timedelta(days=interval)

    jira_db = jira.JIRA(server=gServer, basic_auth=(gU, gP))

    ''' get the list of issues that have a worklog during the prior week'''
    issue_list = jira_db.search_issues('project=LIFT', maxResults=False)

    print("Date Range: {0}-{1}".format(wstart.strftime("%m/%d/%Y"), wend.strftime("%m/%d/%Y")))

    for issue in issue_list:
        if len(issue.fields.issuelinks) > 0:
            for link in issue.fields.issuelinks:
                try:
                    target = link.outwardIssue.key
                    direction = 'outward'
                except AttributeError:
                    try:
                        target = link.inwardIssue.key
                        direction = 'inward'
                    except AttributeError:
                        target = "No link"
                        direction = "No direction"
                print("{0} {1} {2} to {3}".format(issue.key, link.type.name, direction, target))


if __name__ == '__main__':
    args = command_line()
    gU = args.user
    gP = args.password

    if args.missing:
        missing_time_report(7)
    if args.lift:
        lift_report(7)

        # jira_allocation_report()
