import requests
import json
import threading
from abc import abstractmethod
from time import sleep


"""    
    This package is an interface for the monday api.
    It's purpose is to make things easier and more practical about the api usage.
    The main idea behind this approach, is to create a server which receives input from a monday user, and update
    output on the monday workspace - automatically and possibly input related.
    At the end, your server is intended to use this package to interact with monday, and the clients, aka the monday
    users, are intended to interact with your server and receive updates on their monday account (boards, items, etc.).
    
    Note that in a way the interface is pretty basic, it does not include basic operations such as board deletion,
    hopefully in further updates it will improve.
    
    Please, feel free to use the interface for your personal purposes. I highly encourage you expand the features of the
    tool and modify it for your own needs. But please do not copy and publish it without contacting me.
    If you are willing to share your new features, please contact me and I will add them to the tool (and will add 
    credit of course).
    
    Author: © Maor Raviach.
    mail address: maor29468@gmail.com. 
"""


class MyThread(threading.Thread):
    """
        This class creates threads.
    """

    def __init__(self, thread_id=-1, thread_name="thread", **kwargs):
        """
            Initialize the thread.
        """

        # Call the super constructor with self.
        super(MyThread, self).__init__(**kwargs)

        # The id of the thread.
        self.thread_id = thread_id

        # The name of the thread.
        self.thread_name = thread_name

    def run(self):
        """
            Overrides the start() function of the threading.thread. To Execute the thread, call start() not run().
        """

        self.manager()

    @abstractmethod
    def manager(self):
        """
            The function is intended for overriding by extended classes.
        """


class WorkSpace:
    """
        A workspace.

        Do not initialize a workspace which has no board on monday. monday does not recognize a workspace as workspace
        if it has not boards at all.
    """

    def __init__(self, name, token, boards_limit=500, print_api_protocol=False):
        """
            Define the workspace.
        """

        # The name of the workspace. Helps to track the required workspace to work on from monday.
        self.name = name

        # The token of the Monday user.
        self.token = token

        # The link of the most recent api.
        self.apiUrl = "https://api.monday.com/v2"

        # Headers for the post requests.
        self.headers = {"Authorization": self.token}

        # The maximum amount of boards on the current token.
        self.boards_limit = boards_limit

        # If True, prints the data transmission with the api.
        self.print_api_protocol = print_api_protocol

        # A dictionary with all the boards in the workspace {board_name: board instance}.
        self.boards = {}

        # Update the boards list to match the current status of boards in the workspace.
        self.update_boards_in_ws()

        # Get the id of the workspace.
        self.work_space_id = self.get_ws_id()

    def post_request(self, query):
        """
            The function receives a graph-ql query, sends a post request to the monday user with the ws token. It
            returns the response as a string.
        """

        # Follow the format.
        data = {'query': query}

        if self.print_api_protocol:
            print("sending:", query)

        # Send the post request and save the response as the received json string.
        response_str = requests.post(url=self.apiUrl, json=data, headers=self.headers).text

        # Convert the json string to the original object.
        response = json.loads(response_str)

        # Check if any errors occurred. Handle them correctly.
        if not self.handle_response_errors(response=response):

            # An error occurred. Try to post the request again.
            return self.post_request(query=query)

        # Return the answer.
        try:
            if self.print_api_protocol:
                print("received:", response)
                print()
            return response['data']

        except:

            # Probably an untracked error.
            if self.print_api_protocol:
                print("untracked error in post request:")
                print("query:", query)
                print("error: ", response)
                print()

    def handle_response_errors(self, response):
        """
            The function receives a response from the api.
            It checks if any errors were received.
            It handles the errors, e.g. sleeps if received complexity budget exhausted error.
            Returns True if it is not required to re-upload the request, and return False otherwise.
        """

        # Something went wrong. Check if can identify what's up.
        if 'errors' in response:

            # Get the errors list.
            errors = response['errors']

            # Iterate over the errors.
            for error in errors:

                # Usually the error is described in message.
                if 'message' in error:

                    # The error message.
                    error_message = error['message']

                    # To much data was sent lately. The api needs a rest.
                    if 'Complexity budget exhausted' in error_message:

                        # If the number of seconds won't be identified, wait 5 seconds as default.
                        seconds_to_rest = 5

                        # The required number of seconds to rest is specified.
                        if 'reset in ' in error_message:

                            # Try to extract the specified amount of seconds to rest.
                            seconds_to_rest = error_message.split('reset in ')[1][0]

                            # Check if it is really a number.
                            if seconds_to_rest.isdigit():

                                # Get the number of seconds to rest and add 1 just in case
                                # (sometimes returns 0 seconds to rest, we want to give it chills).
                                seconds_to_rest = int(seconds_to_rest) + 1

                        # Rest.
                        sleep(seconds_to_rest)

                        # Need to make the post request again.
                        return False

                    # Undefined error.
                    else:

                        # Save the error in the errors file for later observation.
                        with open("errors.txt", "a") as file1:
                            file1.write(error_message)

            # Nevertheless, try again to post the request.
            return False

        # Seems like everything is fine.
        return True

    def get_ws_id(self):
        """
            The function returns the id of the workspace.
        """

        # The are no boards currently in the workspace. Things won't work out here.
        if not self.boards:
            print("Please create at least one board, can't locate an empty workspace.")
            return

        # Just get the workspace id via one of the workspace boards.
        return self.post_request(
            query='{ boards (ids:' + list(self.boards.values())[0].board_id + '){id name workspace {id name} }}')[
            'boards'][0]['workspace']['id']

    def update_boards_in_ws(self):
        """
            The function extracts the currently existing boards in the workspace.
            It creates for each board, a Board instance and initializes it.
            It returns a list with all the boards.
        """

        # Reset the current status of the boards.
        self.boards = {}

        # Get the ids and names of all the boards in the current monday account (identified by the received token).
        boards_names = self.post_request(query='{ boards (limit:' + str(self.boards_limit) +
                                               ') {id name workspace {id name} }}')

        # Iterate over the boards. It is required to get board by board and not all at once,
        # because there are heavy boards sometimes, and monday doesn't like to make too large responses.
        for board in boards_names['boards']:

            # First, make sure that the current board is from the current workspace.
            if not board['workspace'] or not board['workspace']['name'] == self.name:

                # Try the next board.
                continue

            # Get the data of the board with graph-ql format.
            boards_data = self.post_request(query='{ boards (ids:' + board[
                'id'] + ') {id name groups{id title} columns{id title type description} items{id name group{ id title }'
                        ' column_values{id text}} }}')

            # Extract the board data only from the response.
            full_board_data = boards_data['boards'][0]

            # Create the current board and append it to the boards list.
            self.boards[board["name"]] = Board(ws=self, name=board['name'], board_id=board['id'],
                                               json_groups=full_board_data['groups'],
                                               json_columns=full_board_data['columns'],
                                               json_items=full_board_data['items'])

    def add_board(self, board):
        """
            The function receives a board and adds it to the workspace.
        """

        self.boards[board.name] = board


class Board:
    """
        Represents a board in a work_space.
    """

    def __init__(self, ws, name, exists=False, json_groups=None, json_columns=None, json_items=None, board_id=None):
        """
            Create an instance to an existing board.
        """

        # The work_space of the board.
        self.work_space = ws

        # The name of the board, its title.
        self.name = name

        # A dictionary with all the columns of the board {column title: column instance}.
        self.columns = {}

        # A dictionary with all the groups of the board {group title: group instance}.
        self.groups = {}

        # This board is already on monday, get its values from monday.
        if json_groups:

            # The id of the board, used for identifying the board with the api.
            self.board_id = board_id

            # Set the columns of the board.
            self.set_columns(json_columns)

            # Set the received groups as the groups of the board.
            self.set_groups(json_groups)

            # Set the received items.
            self.set_items(json_items)

        # Create the board on monday too.
        else:

            # The board does not already exist in monday.
            if not exists:

                # Create the query.
                query = 'mutation { create_board (board_name: "' + self.name + \
                        '", board_kind: private, workspace_id: ' + str(self.work_space.work_space_id) + ') { id } }'

                # Update the board on monday and save its id.
                self.board_id = self.work_space.post_request(query)['create_board']['id']

                # Remove any default groups.
                for group in \
                        self.work_space.post_request(query='{ boards (ids: ' + self.board_id +
                                                           ') {id groups{id title}} }')[
                            'boards'][0]['groups']:
                    self.work_space.post_request(
                        query='mutation { delete_group (board_id: ' + self.board_id + ', group_id: "' + group[
                            "id"] + '") { id deleted } }')

            else:

                # Get the ids and names of all the boards in the current monday account.
                boards_names = self.work_space.post_request(query='{ boards {id name workspace {id name} }}')

                # Iterate over the boards.
                for board in boards_names['boards']:

                    # First, make sure that the current board is from the current workspace.
                    if not board['workspace'] or not board['workspace']['name'] == self.work_space.name:

                        # Try the next board.
                        continue

                    # If this is not the current board.
                    if board['name'] != self.name:
                        continue

                    self.board_id = board['id']

                    # Remove any default groups.
                    for group in \
                            self.work_space.post_request(
                                query='{ boards (ids: ' + self.board_id + ') {id groups{id title}} }')[
                                'boards'][0]['groups']:

                        self.work_space.post_request(
                            query='mutation { delete_group (board_id: ' + self.board_id + ', group_id: "' + group[
                                "id"] + '") { id deleted } }')

                    # Board founded, no need to keep searching.
                    break

            # Add the board to the work_space.
            self.work_space.add_board(self)

    def set_columns(self, json_columns):
        """
            The function receives a json list of columns. It creates and adds the columns to the board.
        """

        # Iterate over the columns.
        for column in json_columns:

            # Create and append the current column.
            self.columns[column['title']] = Column(board=self, title=column['title'], description=column['description'],
                                                   column_type=column['type'], column_id=column['id'])

    def set_groups(self, json_groups):
        """
            The function receives a json list of groups. It creates and adds the groups to the board.
        """

        # Iterate over the groups.
        for group in json_groups:

            # Create and append the current group.
            self.groups[group['title']] = Group(board=self, group_id=group['id'], title=group['title'])

    def set_items(self, json_items):
        """
            The function receives a json list of items. It creates and adds the items to their groups.
        """

        # Iterate over all the items in the board.
        for item in json_items:

            # The group of the item.
            item_group_title = item['group']['title']

            # Create the new item.
            new_item = Item(group=item_group_title, name=item['name'], item_id=item['id'],
                            json_columns_values=item['column_values'])

            # Add it to the group.
            self.groups[item_group_title].add_item(new_item)

    def add_column(self, column):
        """
            The function receives a column and adds it to the board.
        """

        self.columns[column.title] = column

    def add_group(self, group):
        """
            The function receives a group and adds it to the board.
        """

        self.groups[group.title] = group


class InputBoard(MyThread, Board):
    """
        A board that gets input from the user in monday.
    """

    def __init__(self, ws, name, execution_dict, check_rate=1):
        """
            Initialize the input board.
        """

        # Initialize input board as a thread.
        MyThread.__init__(self)

        # Initialize input board as a board.
        Board.__init__(self, ws=ws, name=name)

        # Create a status bar column.
        self.add_column(Column(board=self, title="Execution Status", description="", column_type="status"))

        # Save the id of the status column.
        self.status_column_id = self.columns["Execution Status"].column_id

        # The execution dictionary.
        # Form: {'group title': reference to a function which handles the submission of a new item in that group.
        # Note that this function receives an item's name}
        self.execution_dict = execution_dict

        # The board check if a new input was entered every <check_rate> seconds.
        self.check_rate = check_rate

    def manager(self):
        """
            The thread body. Do not call manager() on the input board. Call to start() instead.
        """

        # Every <self.check_rate> seconds, checkout the items on the board.
        while True:

            # Get all the items on the board.
            items_json = self.work_space.post_request(
                query='{ boards (ids: ' + self.board_id +
                      ') {id items{id name group {id title} column_values {title value}}} }')[
                'boards'][0]['items']

            # Iterate overt the input items.
            for current_item in items_json:

                # That's a new item.
                if not current_item['column_values'][0]['value']:

                    # Update the status of the item to working on it.
                    self.work_space.post_request(
                        query='mutation { change_column_value (board_id: ' + self.board_id + ', item_id: ' +
                              current_item[
                                  'id'] + ', column_id: "' + self.status_column_id +
                              '", value: "{\\\"index\\\" : 0}") { id } }')

                    # Call the function that handles the item submission as a thread.
                    analyser = Analyzer(input_board=self, item_id=current_item['id'],
                                        function=self.execution_dict[current_item['group']['title']],
                                        inputs={"item_name": current_item['name']})

                    # start the function as a thread.
                    analyser.start()

            # Take a rest for a <self.check_rate> seconds before the next check.
            sleep(self.check_rate)

    def update_handled_successfully(self, item_id):
        """
            The function receives an id of an item and updates its status to done in the input board.
        """

        self.work_space.post_request()


class ThreadBoard(MyThread, Board):
    """
        A board with option to run as thread.
    """

    def __init__(self, ws, name, thread_function, function_parameters, exists=False):
        """

        """

        # Initialize input board as a thread.
        MyThread.__init__(self)

        # Initialize input board as a board.
        Board.__init__(self, ws=ws, name=name, exists=exists)

        # A reference to the thread function.
        self.thread_function = thread_function

        # The parameters of the execution function.
        self.function_parameters = function_parameters

    def manager(self):
        """
            The main loop of the board thread.
        """

        self.thread_function(board=self, **self.function_parameters)


class Analyzer(MyThread):
    """
        An analyser warps a function as a thread.
    """

    def __init__(self, input_board, item_id, function, inputs):
        """
            Receives the function to execute and its inputs as dictionary of the form {parameter: value}.
            Holds a reference to the input board, and has the id of the item that caused to the spawn of the analyzer.
        """

        # Initialize the thread.
        MyThread.__init__(self)

        # Save the data of the analyser.
        self.input_board = input_board
        self.item_id = item_id
        self.function = function
        self.inputs = inputs

    def manager(self):
        """
            The function executes the function of the analyser.
        """

        # Execute the function.
        self.function(**self.inputs)

        # Update the status of the analyser to Done.
        self.input_board.work_space.post_request(
            query='mutation { change_column_value (board_id: ' + self.input_board.board_id + ', item_id: ' +
                  self.item_id + ', column_id: "' + self.input_board.status_column_id +
                  '", value: "{\\\"index\\\" : 1}") { id } }')


class Group:
    """
        Represents a group of a board.
    """

    def __init__(self, board, title, group_id=None):
        """
            Initialize the group.
        """

        # The board that the group is within.
        self.board = board

        # The title of the group.
        self.title = title

        # A list with all the items of the group.
        self.items = {}

        # The group already exists on monday, get its details.
        if group_id:

            # The id of the group.
            self.group_id = group_id

        # The group does not exist in monday.
        else:

            # Update it on monday.
            self.group_id = self.board.work_space.post_request(
                query='mutation { create_group (board_id: ' + self.board.board_id + ', group_name: "' +
                      self.title + '") { id } }')['create_group']['id']

    def set_items(self, json_items):
        """
            The function receives a json list of items. It creates and adds the items to the group.
        """

        # If no items received, return an empty list.
        if not json_items:
            return []

        # The final list with the items instances.
        items = {}

        # Iterate over the items.
        for item in json_items:
            # Create the item and append it to the items list.
            items[item['name']] = Item(group=self, item_id=item['id'], name=item['name'])

        # Return the list of items.
        return items

    def get_id(self):
        """
            The function returns the id of the group.
        """

        # Get from monday the titles and ids of the groups.
        groups = \
            self.board.work_space.post_request(
                query='{ boards (ids: ' + self.board.board_id + ') {id groups {id title}}}')[
                'boards'][0]['groups']

        # Iterate over the groups of the board.
        for group in groups:

            # Locate the current group.
            if group['title'] == self.title:
                # And return its id.
                return group['id']

        # The group for some reason is not on the board.
        return ''

    def add_item(self, item):
        """
            The function receives an item and adds it to the group.
        """

        self.items[item.name] = item


class Column:
    """
        Represents a column of a board.
    """

    def __init__(self, board, title, description, column_type, column_id=None):
        """
            Initialize the column.
        """

        # The board of the column.
        self.board = board

        # The title of the column.
        self.title = title

        # The description of the column.
        self.description = description

        # The type of the column.
        self.column_type = column_type

        # The column already exists in monday.
        if column_id:

            self.column_id = column_id

        # Create the column in monday.
        else:

            self.column_id = self.board.work_space.post_request(
                query='mutation{ create_column(board_id: ' + self.board.board_id + ', title:"' + self.title +
                      '", description: "' + self.description + '", column_type:' + self.column_type +
                      ') { id title description } }')['create_column']['id']


class Item:
    """
        Represents an item of a group.
    """

    def __init__(self, group, name, item_id=None, json_columns_values=None, columns_values=[]):
        """
            Initialize the item.
            Note: One of json_column_values or column_values must be specified. column_values is of the form: [(column title, value)].
        """

        # The group the item is within.
        self.group = group

        # The id of the item.
        self.item_id = item_id

        # name of the item
        self.name = name

        # The columns values of the item {column id: item's value}.
        self.columns_values = {}

        # The item already exists in monday.
        if item_id:

            # Save its id.
            self.item_id = item_id

            # Extract its column values.
            self.set_columns(json_columns_values)

        # Update the item in monday.
        else:

            columns_values_json = '{'

            for column_title, value in columns_values:

                if type(value) is str:
                    columns_values_json += '\\\"' + self.group.board.columns[
                        column_title].column_id + '\\\": \\\"' + value + '\\\"' + ', '
                elif type(value) is dict:
                    columns_values_json += '\\\"' + self.group.board.columns[
                        column_title].column_id + '\\\": ' + json.dumps(value) + ', '

            # Remove the last ,.
            if len(columns_values_json) > 1:
                columns_values_json = columns_values_json[:-2]

            columns_values_json += '}'

            # Add the item to monday and save its id.
            self.item_id = self.group.board.work_space.post_request(
                query='mutation {create_item (board_id: ' + self.group.board.board_id + ', group_id: "' +
                      self.group.group_id + '", item_name: "' + self.name + '", column_values: "' +
                      columns_values_json + '") { id } }')['create_item']['id']

    def set_columns(self, json_columns_values):
        """
            The item is already in monday. The function receives its columns values and saves them.
        """

        # Iterate over the columns values.
        for column_value in json_columns_values:

            # Save the column id and its value.
            self.columns_values[column_value['id']] = column_value['text']

    def upload_files(self, column_title, files_paths):
        """
            The function receives a list with files paths and a column and uploads the file to that column.
        """

        # Upload all the files.
        for file_path in files_paths:

            self.upload_file(column_title=column_title, file_path=file_path)

    def upload_file(self, column_title, file_path):
        """
            The function uploads a single file to the received column.
        """

        # The query that makes the request to upload the file to the specific received column.
        query = 'mutation ($file: File!) { add_file_to_column (file: $file, item_id: ' + self.item_id + \
                ', column_id: "' + self.group.board.columns[column_title].column_id + '") {id }}'

        # A list with all the files in the required format.
        files = [('variables[file]', (file_path, open(file_path, 'rb'), 'multipart/form-data'))]

        # Follow the format.
        data = {'query': query}

        if self.group.board.work_space.print_api_protocol:
            print("sending:", query)

        # Send the post request and save the response as the received json string.
        response_str = requests.post(url="https://api.monday.com/v2/file",
                                     headers={'Authorization': self.group.board.work_space.token}, data=data,
                                     files=files).text

        # Convert the json string to the original object.
        response = json.loads(response_str)

        # Check if any errors occurred.
        if not self.group.board.work_space.handle_response_errors(response=response):
            # An error occurred, try to upload the file again.
            return self.upload_file(column_title=column_title, file_path=file_path)

        if self.group.board.work_space.print_api_protocol:
            print("response:", response)

    def add_update(self, content):
        """
            The function receives a content and adds it to the update window of the item.
        """

        # The query to add the update.
        query = 'mutation { create_update (item_id: ' + self.item_id + ', body: "' + content + '") { id } }'

        # Execute.
        self.group.board.work_space.post_request(query=query)

    def add_link(self, column_title, link, description=''):
        """
            The function receives a column, link and a description. It updates the received link in the received column in monday.
        """

        # The query to insert the link.
        if description:
            query = 'mutation { change_column_value (board_id: ' + self.group.board.board_id + ', item_id: ' + \
                    self.item_id + ', column_id: "' + \
                    self.group.board.columns[
                        column_title].column_id + '", value: "{\\\"url\\\":\\\"' + link + '\\\",\\\"text\\\":\\\"' + \
                    description + '\\\"}") { id } }'
        else:
            query = 'mutation { change_column_value (board_id: ' + self.group.board.board_id + ', item_id: ' + \
                    self.item_id + ', column_id: "' + \
                    self.group.board.columns[
                        column_title].column_id + '", value: "{\\\"url\\\":\\\"' + link + '\\\",\\\"text\\\":\\\"' + \
                    link + '\\\"}") { id } }'

        # Execute.
        self.group.board.work_space.post_request(query=query)

    def set_rating(self, column_title, value):
        """
            The function receives a rating column title and a value. It updates the rating value of the item.
        """

        query = 'mutation { change_column_value (board_id: ' + self.group.board.board_id + ', item_id: ' + \
                self.item_id + ', column_id: "' + \
                self.group.board.columns[
                    column_title].column_id + '", value: "{\\\"rating\\\":' + value + '}") { id } }'

        # Execute.
        self.group.board.work_space.post_request(query=query)


# Usage Explanation & Example.


# Documentation for the graph=ql: https://api.developer.monday.com/docs/items-queries


# ----- Boards columns groups and items creation -----

# First, you'd probably like to create a reference to your workspace.
# Important note: Monday does not recognize an empty work space. An existing workspace is one with at least one board.
# Therefore, do not except to track your workspace if it's empty.
# Moreover, the default workspace is recognized as None. It is recommended to create a new workspace.
work_space = WorkSpace(name="Workspace name here", token="Your token here")

# Now you can create boards.
my_board = Board(ws=work_space, name="My terrific board")

# And you can create columns to the boards.
my_board.add_column(Column(board=my_board, title="Date", description="When the row was added to the board",
                           column_type="date"))
my_board.add_column(Column(board=my_board, title="Favourite color", description="the favourite color of the row",
                           column_type="text"))
my_board.add_column(Column(board=my_board, title="Link", description="A link to a website", column_type="link"))
my_board.add_column(Column(board=my_board, title="Attached Files", description="", column_type="file"))

# These columns are saved in my_board.columns. This is a dictionary of the form: {column title: column instance}.

# And you can create groups.
my_board.add_group(Group(board=my_board, title="An amazing group"))
my_board.add_group(Group(board=my_board, title="Another amazing group"))

# These groups are saved in my_board.groups. This is a dictionary of the form: {group title: group instance}.

# Now you can add items to groups. Note that there are columns which requires unique protocol, such as links and files.
my_board.groups["An amazing group"].add_item(Item(group=my_board.groups["An amazing group"], name="Spectacular item 1",
                                                  columns_values=[("Date", "2022-05-04"), ("Favourite color", "Blue")]))
my_board.groups["An amazing group"].add_item(Item(group=my_board.groups["An amazing group"], name="Spectacular item 2"))

# These items are saved in my_board.groups["An amazing group"].items. This is a dictionary of the form:
# {item name: item instance}.

# You can upload a file to an item's column (you can upload multiple files to one column).
my_board.groups["An amazing group"].items["Spectacular item 1"].upload_files(column_title="Attached Files",
                                                                             files_paths=["file1.txt", "file2.txt"])

# You can add a link to an item's column (multiple links for one column currently unsupported with monday).
my_board.groups["An amazing group"].items["Spectacular item 1"].add_link(column_title="Link", link="www.google.com",
                                                                         description="search with google")


# ----- Input manipulation -----


def input_group_handle_new_item(item_name):
    """
        The function receives the title of the added item. It adds a new item to Terrific Board under another amazing
        group.
    """

    my_board.groups["An amazing group"].add_item(Item(group=my_board.groups["Another amazing group"], name=item_name))


# For Getting input you'd probably like to use InputBoard. This board is a board on monday which is also a thread.
# Each second (or whatever interval you wish) the thread checks if a new item was added to one of the groups in the
# board. If it did, it calls to a function which knows how to handle the input, as a thread.
# Note that an input board is also a standard board itself, not all the groups within must exist for input.
input_board = InputBoard(ws=work_space, name="Input", execution_dict={'Input Group 1': input_group_handle_new_item})

# Create input group. Note that its name should match the reference in execution_dict if you wish to receive input with
# this group.
input_board.add_group(Group(board=input_board, title="Input Group 1"))

# Now, when the user adds an item to Input Group 1 in monday, input board automatically calls to
# input_group_handle_new_item(item_name=new_item_title) as a thread.
input_board.start()
