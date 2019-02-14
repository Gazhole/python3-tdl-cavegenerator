from tdl.map import Map
from random import randint, shuffle, choice
from entities.classes import Actor
from game_functions.render import RenderOrder


# At the moment this is the game map, based off the map class in TDL with some additions (much easier than using a Tile)
class GameMap(Map):
    def __init__(self, width, height):
        super().__init__(width, height)
        self.width = width
        self.height = height
        self.explored = [[False for y in range(height)] for x in range(width)]


# This is the top level function to generate a cave map. Carve out a series of branches which interlink with eachohter.
# Few arguments to determine how this works but generally its pretty simple.
def make_cave(game_map, map_config, monster_config, player, entities):

    map_width, map_height, max_monsters_per_branch, max_items_per_branch = map_config.map_variables
    map_width -= 1
    map_height -= 1

    cave_coords = []  # List to store viable coordinates for item, monster, player placement.

    # Random seeds for the cave parameters
    num_branches = int(((map_width + map_height) / 2) / 10)  # How many branches? Pick based on map size
    windyness = randint(40, 80)  # The extent that the branch position will move a lot.
    roughness = randint(40, 80)  # The extent that the branch width will vary
    magnitude = randint(2, 4)  # The step value for branch path movement.

    # Set the boundaries so branches occur within the map size.
    # Ultimate actual boundaries of the map are width and height - 1 tile.
    branch_min_x = 2
    branch_max_x = map_width - 1
    branch_min_y = 2
    branch_max_y = map_height - 1

    # To make sure a large portion of the cave is reachable, 75% of the branches will be joined together.
    connected_branches = int(num_branches * 0.75)

    # Main loop to create branches.
    for branch in range(connected_branches):

        # First we need to randomly decide whether this branch is horizontal or vertical.
        if randint(0, 1) == 0:

            # The create_?_cave_branch functions also return the list of coordinates carved out, which we will append
            # to the coords for the entire cave. This is true for connected branches, as in this way we will ensure that
            # all branches start or intersect an already used point on the map.

            current_branch_coords = create_v_cave_branch(game_map,
                                                         branch_min_x, branch_max_x, branch_min_y, branch_max_y,
                                                         magnitude, windyness, roughness, cave_coords)

            # Place entities (monsters, items) in the newly created branch.
            place_entities(current_branch_coords, entities, max_monsters_per_branch, max_items_per_branch,
                           monster_config)

            cave_coords += current_branch_coords

        else:
            current_branch_coords = create_h_cave_branch(game_map,
                                                         branch_min_x, branch_max_x, branch_min_y, branch_max_y,
                                                         magnitude, windyness, roughness, cave_coords)

            place_entities(current_branch_coords, entities, max_monsters_per_branch, max_items_per_branch,
                           monster_config)
            cave_coords += current_branch_coords

    # Once all the connected branches have been created, pop a coordinate off the list and put the player there.
    player.x, player.y = cave_coords.pop()

    # Unconnected branches are placed randomly, they will likely be connected with the rest of the map, but not
    # necessarily. Because of the algorithm used for connected branches i've found doing a few random branches
    # makes the map a lot more interesting.
    unconnected_branches = num_branches - connected_branches

    for branch in range(unconnected_branches):
        if randint(0, 1) == 0:

            # Make sure the branches aren't connected by clearing the cave coordinate list, and also don't assign a var
            # to return the list of new branch coordinates to.
            cave_coords.clear()
            create_v_cave_branch(game_map,
                                 branch_min_x, branch_max_x, branch_min_y, branch_max_y,
                                 magnitude, windyness, roughness, cave_coords)

            # We could probably place some more items and monsters into the unconnected branches, but it shouldn't hurt
            # to have a few "safer" sections for the player to escape into.
        else:
            cave_coords.clear()
            create_h_cave_branch(game_map,
                                 branch_min_x, branch_max_x, branch_min_y, branch_max_y,
                                 magnitude, windyness, roughness, cave_coords)

        # Make sure there's a border all the way around the map.
        for x in range(0, map_width):
            game_map.walkable[x][0] = False
            game_map.walkable[x][map_height] = False

        for y in range(0, map_height):
            game_map.walkable[0][y] = False
            game_map.walkable[map_width][y] = False

    # The following code is optional, and is used for debugging purposes only - prints out some info on the map, and
    # dumps a basic ASCII image to a txt file to view the whole map without FOV getting in the way.

    count_monsters = 0
    count_items = 0
    for entity in entities:
        if entity.name.lower() != "player":
            count_monsters += 1
        # if entity.name.lower() != "player" and entity.item:
        #     count_items += 1

    print("MAP SIZE:", map_width, "x", map_height,
          "\nTOTAL BRANCHES:", num_branches, "(CONNECTED/UNCONNECTED:", connected_branches, "/", unconnected_branches, ")",
          "\nWINDYNESS/ROUGHNESS/MAGNITUDE:", windyness, "/", roughness, "/", magnitude,
          "\nMONSTERS:", count_monsters,
          "\nITEMS:", count_items)

    draw_cave(game_map, map_width, map_height, num_branches, connected_branches, unconnected_branches,
              windyness, roughness, magnitude, count_monsters, count_items, entities)


# Set all the required parameters for a new cave branch
def setup_branch(cave_coords, branch_min_x, branch_min_y, branch_max_x, branch_max_y, branch_type):

    branch_starting_width = randint(4, 8)

    if branch_type == "h":  # Horizontal, obviously.
        if cave_coords:  # If this list isn't populated, it means this is the first branch, or unconnected.
            shuffle(cave_coords)
            seed_x, seed_y = cave_coords.pop()  # Set a random seed coordinate for this branch, connecting to the rest

            # If the seed coordinates are in the left or top half of the screen, we should be fine to start the new
            # branch where it is. However, if in the case of a horizontal branch starting in the right half of the map
            # if we did this, the branch would be very short and things would cluster to one side.
            # The solution in the horizontal branch example, is to keep Y the same, but shift X to a coordinate
            # mirrored on the left side of the screen (e.g. with a map width of 100 an x of 60 changes to 40, 80 to 20..
            half_available_space = int(branch_max_x * 0.5)

            if seed_x > int(branch_max_x * 0.5):  # If in the right half of the map
                branch_starting_x = seed_x - ((seed_x - half_available_space) * 2)  # This is the important calculation
                branch_starting_y = int(seed_y)
            else:
                branch_starting_x = int(seed_x)
                branch_starting_y = int(seed_y)

            branch_length = (branch_max_x - branch_starting_x) - 3

            check_valid_coords(branch_min_x, branch_max_x, branch_min_y, branch_max_y,
                               branch_starting_x, branch_starting_y, branch_starting_width, branch_type)

        # If we don't have a seed coord, just pick some random coordinates skewed to the left / top.
        else:
            branch_starting_x = branch_min_x + randint(branch_min_x, int(branch_max_x * 0.75))
            branch_starting_y = branch_min_y + randint(branch_min_y, int(branch_max_y * 0.75))
            branch_length = (branch_max_x - branch_starting_x) - 3

        return branch_starting_x, branch_starting_y, branch_length, branch_starting_width

    if branch_type == "v":
        if cave_coords:
            shuffle(cave_coords)
            seed_x, seed_y = cave_coords.pop()

            half_available_space = int(branch_max_y * 0.5)

            if seed_y > int(branch_max_y * 0.5):
                branch_starting_y = seed_y - ((seed_y - half_available_space) * 2)
                branch_starting_x = int(seed_x)
            else:
                branch_starting_y = int(seed_y)
                branch_starting_x = int(seed_x)

            branch_length = int((branch_max_y - branch_starting_y) - 3)

            check_valid_coords(branch_min_x, branch_max_x, branch_min_y, branch_max_y,
                               branch_starting_x, branch_starting_y, branch_starting_width, branch_type)

        else:
            branch_starting_x = branch_min_x + randint(branch_min_x, int(branch_max_x * 0.75))
            branch_starting_y = branch_min_y + randint(branch_min_y, int(branch_max_y * 0.75))
            branch_length = (branch_max_y - branch_starting_y) - 3

        return branch_starting_x, branch_starting_y, branch_length, branch_starting_width


# Just some checking to make sure the iterative part of the cave generation doesn't go outside the boundaries of the map
def check_valid_coords(branch_min_x, branch_max_x, branch_min_y, branch_max_y,
                       current_x, current_y, current_width, branch_type):

    if branch_type == "v":
        if current_width < 3:
            current_width = 3

        if current_x <= branch_min_x:
            current_x = branch_min_x + 1

        if current_x + current_width >= branch_max_x:
            current_x = branch_max_x - current_width - 1
            current_width = branch_max_x - current_x

    if branch_type == "h":
        if current_width < 3:
            current_width = 3

        if current_y < branch_min_y:
            current_y = branch_min_y + 1

        if current_y + current_width >= branch_max_y:
            current_y = branch_max_y - current_width - 1
            current_width = branch_max_y - current_y

    return current_width, current_x, current_y


# Once the branches have been set up, this is the function which actually iterates through and carves out a dungeon
def create_v_cave_branch(game_map, branch_min_x, branch_max_x, branch_min_y, branch_max_y,
                         magnitude, windyness, roughness, cave_coords):

    branch_coords = []  # Empty list to store coords

    # Get all the configuration values from the setup function
    branch_starting_x, branch_starting_y, branch_length, branch_starting_width = \
        setup_branch(cave_coords, branch_min_x, branch_min_y, branch_max_x, branch_max_y, branch_type="v")

    # Carve out the first slice (a vertical branch is essentially a stack of horizontal slices/tunnels).
    create_h_tunnel(game_map, branch_starting_x, branch_starting_x + branch_starting_width, branch_starting_y)

    current_x = int(branch_starting_x)
    current_y = int(branch_starting_y)
    current_width = int(branch_starting_width)

    for i in range(branch_length):
        current_y += 1  # Move down one row / slice.

        # The higher the roughness, the more likely this bit will be called. This is how often the width will change.
        if randint(1, 100) <= roughness:
            width_delta_range = list(range(-magnitude, magnitude))  # make a list of potential deltas
            width_delta_range.remove(0)  # We don't want the width of the slice to stay the same.
            shuffle(width_delta_range)

            width_delta = width_delta_range.pop()
            current_width += width_delta

        # The windyness is how much the starting position of the slice will move.
        if randint(1, 100) <= windyness:
            current_x_delta_range = list(range(-magnitude, magnitude))
            current_x_delta_range.remove(0)
            shuffle(current_x_delta_range)

            current_x_delta = current_x_delta_range.pop()
            current_x += current_x_delta

        # Check whether this new slice is valid within the map.
        current_width, current_x, current_y = check_valid_coords(branch_min_x, branch_max_x, branch_min_y, branch_max_y,
                                                                 current_x, current_y, current_width, branch_type="v")

        # Create the slice by carving out from the x, on the y, with a length of width.
        create_h_tunnel(game_map, current_x, current_x + current_width, current_y)

        # Append the coords.
        for x in range(current_x, current_x + current_width + 1):
            branch_coords.append((x, current_y))

    # Round off the end of the branch (no flat edges)
    if current_width > 3:
        while branch_min_y < current_y < branch_max_y - 1:
            current_y += 1
            current_x += 1

            if current_width - magnitude <= 1:
                current_width = 1
            else:
                current_width -= magnitude

            create_h_tunnel(game_map, current_x, current_x + current_width, current_y)

            # Append the coords.
            for x in range(current_x, current_x + current_width + 1):
                branch_coords.append((x, current_y))

    return branch_coords


def create_h_cave_branch(game_map, branch_min_x, branch_max_x, branch_min_y, branch_max_y,
                         magnitude, windyness, roughness, cave_coords):

    branch_coords = []

    branch_starting_x, branch_starting_y, branch_length, branch_starting_width = \
        setup_branch(cave_coords, branch_min_x, branch_min_y, branch_max_x, branch_max_y, branch_type="h")

    create_v_tunnel(game_map, branch_starting_y, branch_starting_y + branch_starting_width, branch_starting_x)

    current_x = int(branch_starting_x)
    current_y = int(branch_starting_y)
    current_width = int(branch_starting_width)

    for i in range(branch_length):
        current_x += 1

        if randint(1, 100) <= roughness:
            width_delta_range = list(range(-magnitude, magnitude))
            width_delta_range.remove(0)
            shuffle(width_delta_range)

            width_delta = width_delta_range.pop()
            current_width += width_delta

        if randint(1, 100) <= windyness:
            current_y_delta_range = list(range(-magnitude, magnitude))
            current_y_delta_range.remove(0)
            shuffle(current_y_delta_range)

            current_y_delta = current_y_delta_range.pop()
            current_y += current_y_delta

        current_width, current_x, current_y = check_valid_coords(branch_min_x, branch_max_x, branch_min_y, branch_max_y,
                                                                 current_x, current_y, current_width, branch_type="h")

        create_v_tunnel(game_map, current_y, current_y + current_width, current_x)

        for y in range(current_y, current_y + current_width + 1):
            branch_coords.append((current_x, y))

    if current_width > 3:
        while branch_min_x < current_x < branch_max_x - 1:
            current_y += 1
            current_x += 1

            if current_width - magnitude <= 1:
                current_width = 1
            else:
                current_width -= magnitude

            create_v_tunnel(game_map, current_y, current_y + current_width, current_x)

            for y in range(current_y, current_y + current_width + 1):
                branch_coords.append((current_x, y))

    return branch_coords


def place_entities(branch_coords, entities, max_monsters_per_branch, monster_config):
    # Get a random number of monsters
    number_of_monsters = randint(0, max_monsters_per_branch)

    for i in range(number_of_monsters):
        # Choose a random location in the branch, and pop that off the list of potential coordinates.
        shuffle(branch_coords)
        x, y = branch_coords.pop()

        if not any([entity for entity in entities if entity.x == x and entity.y == y]):  # Is there anything there?
            monster = pick_monster(x, y, monster_config)

            entities.append(monster)  # This is that list from engine with just the player in it.

    else:
        return None


# This creates a horizontal slice on a vertical branch
def create_h_tunnel(game_map, x1, x2, y):
    for x in range(min(x1, x2), max(x1, x2) + 1):
        game_map.walkable[x][y] = True
        game_map.transparent[x][y] = True


# This creates a vertical slice on a horizontal branch
def create_v_tunnel(game_map, y1, y2, x):
    for y in range(min(y1, y2), max(y1, y2) + 1):
        game_map.walkable[x][y] = True
        game_map.transparent[x][y] = True


# Using the name of a monster pull it's stats and sprite (and later ai type) and place it on the map.
def pick_monster(x, y, monster_config):
    name, char, colour = choice(monster_config["level_1"])

    picked_monster = Actor(x, y, name, char, colour, blocks=True, render_order=RenderOrder.ACTOR)
    return picked_monster


# Create a two dimensional array to write a representation of the game_map to a text file for viewing.
# Currently this is rotated by 90 degrees based on the actual in-game map.
def draw_cave(game_map, map_width, map_height, num_branches, connected_branches, unconnected_branches,
              windyness, roughness, magnitude, count_monsters, count_items, entities):

    cave_drawing = [["" for y in range(map_height)] for x in range(map_width)]

    for y in range(map_height):
        for x in range(map_width):
            if not game_map.transparent[x][y]:
                cave_drawing[x][y] = "#"
            else:
                cave_drawing[x][y] = " "

            for entity in entities:
                if entity.x == x and entity.y == y:
                    cave_drawing[x][y] = entity.char

    with open("map.txt", "w") as map_file:
        for row in cave_drawing:
            for cell in row:
                print(cell, end='', file=map_file)
            print("", file=map_file)

        print("\nMAP SIZE:", map_width, "x", map_height,
              "\nTOTAL BRANCHES:", num_branches, "(CONNECTED/UNCONNECTED:", connected_branches, "/", unconnected_branches, ")",
              "\nWINDYNESS/ROUGHNESS/MAGNITUDE:", windyness, "/", roughness, "/", magnitude,
              "\nMONSTERS:", count_monsters,
              "\nITEMS:", count_items, file=map_file)
