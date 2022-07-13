# Monday-API-Interface
Author: © Maor Raviach.
mail address: maor29468@gmail.com. 

This package is an interface for the Monday api.

It's purpose is to make things easier and more practical about the api usage.

The main idea behind this approach is to create a server that uses the current interface.
By using the interface the server can receive input from any registered Monday user, and modify the Monday workspace.

The interface is currently missing some basic features such as board/groups/columns/items deletion, 
but it has on the other hand some more advanced mechanisms such as input board.

Please, feel free to use the interface for your personal purposes. I highly encourage you to expand the features 
of the tool and modify it for your own needs. But please do not copy and publish it without contacting me.
If you are willing to share your new features, please contact me and I will add them to the tool (and will add 
credit of course).

# User Guide & Example


# Update content on Monday

First, you'd probably like to create a reference to your workspace.

Important notes: Monday does not recognize an empty work space. An existing workspace is one with at least one board.
                 Therefore, do not except to track your workspace if it's empty.
                 Moreover, the default workspace is recognized as None. It is recommended to create a new workspace.
                 To get your token sign in to Monday with your user email and navigate to the developers section.

    work_space = WorkSpace(name="Workspace name here", token="Your token here")

Now you can create boards (Everything created in the code, updates automatically on Monday).

    my_board = Board(ws=work_space, name="My terrific board")

And you can create columns to the boards (Note that you can first create a column and save it in a variable, and then call add_column with that variable).

    my_board.add_column(Column(board=my_board, title="Date", description="When the row was added to the board", column_type="date"))
    
    my_board.add_column(Column(board=my_board, title="Favourite color", description="the favourite color of the row", column_type="text"))
    
    my_board.add_column(Column(board=my_board, title="Link", description="A link to a website", column_type="link"))
    
    my_board.add_column(Column(board=my_board, title="Attached Files", description="", column_type="file"))

These columns are saved in my_board.columns. This is a dictionary of the form: {column title: column instance}.

And you can create groups.

    my_board.add_group(Group(board=my_board, title="An amazing group"))
    
    my_board.add_group(Group(board=my_board, title="Another amazing group"))

These groups are saved in my_board.groups. This is a dictionary of the form: {group title: group instance}.

Now you can add items to groups. Note that there are columns which requires unique protocol, such as links and files.

    my_board.groups["An amazing group"].add_item(Item(group=my_board.groups["An amazing group"], name="Spectacular item 1", columns_values=[("Date", "2022-05-04"), ("Favourite color", "Blue")]))
                                                      
    my_board.groups["An amazing group"].add_item(Item(group=my_board.groups["An amazing group"], name="Spectacular item 2"))

These items are saved in my_board.groups["An amazing group"].items. This is a dictionary of the form: {item name: item instance}.

You can upload a file to an item's column (you can upload multiple files to one column).

    my_board.groups["An amazing group"].items["Spectacular item 1"].upload_files(column_title="Attached Files", files_paths=["file1.txt", "file2.txt"])

You can add a link to an item's column (multiple links for one column currently unsupported with monday).

    my_board.groups["An amazing group"].items["Spectacular item 1"].add_link(column_title="Link", link="www.google.com", description="search with google")


# Input manipulation


    def input_group_handle_new_item(item_name):
        """
            The function receives the title of the added item. It adds a new item to Terrific Board under another amazing group.
        """

        my_board.groups["An amazing group"].add_item(Item(group=my_board.groups["Another amazing group"], name=item_name))


For receiving input from the user you'd probably like to use InputBoard. This board is a board on Monday which is also a thread.
Each second (or whatever interval you wish) the thread checks if a new item was added to one of the groups in the
board. If it did, it calls to a function which knows how to handle the input, as a thread.
Note that an input board is also a standard board itself, not all the groups within must exist for input.

    input_board = InputBoard(ws=work_space, name="Input", execution_dict={'Input Group 1': input_group_handle_new_item})

Create input group. Note that its name should match the reference in execution_dict if you wish to receive input with
this group.
    
    input_board.add_group(Group(board=input_board, title="Input Group 1"))

Now, when the user adds an item to Input Group 1 in monday, input board automatically calls to
input_group_handle_new_item(item_name=new_item_title) as a thread.

    input_board.start()
