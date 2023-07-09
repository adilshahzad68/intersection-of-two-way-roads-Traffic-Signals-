from enum import Enum
from threading import Thread, Condition
from time import sleep
import pygame
from pygame.sprite import Sprite, Group
from pygame.rect import Rect


BACKGROUND_COLOR = (51, 60, 87)


SPEED_SIMULATION = 5


class Color(Enum):
    RED = "r"
    YELLOW = "y"
    GREEN = "g"


class Direction(Enum):
    NORTH = "n"
    SOUTH = "s"
    EAST = "e"
    WEST = "w"

# control 
class Context:
    def __init__(self, velocity: int = SPEED_SIMULATION):
        self.velocity = velocity


class Map(Sprite):
    def __init__(self, src: str = r'D:\\PRACTICE\\conc_p_py\\resources\\map.png', position: tuple = (0, 0), context: Context = None):
        Sprite.__init__(self)
        self.image = pygame.image.load(src).convert_alpha()
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect(center=position)
        self.rect.topleft = (0, 0)
        self.mask = pygame.mask.from_surface(self.image)
        self.context = context

# The  simulation using thread. The main idea is to sync the semaphores
# so only one have one green light and the car avoid collisions with others
# For the thread synchronization process, we use condition  to notify when the thread is available
# and the other thread can process with the execution ,also we shared memory to sync the thread information.
class Semaphore(Thread, Sprite):

    def __init__(self, name: str, direction: Direction, condition: Condition, position: tuple = (0, 0),
                 context: Context = None, color: Color = None, crosswalk: Rect = None):
        self.direction = direction
        self.current_light = color
        self.set_light(color)
        self.rect = self.image.get_rect(center=position)
        self.condition = condition
        self.context = context
        self.crosswalk = crosswalk
        
        #Thread get a args -> condition 
        Thread.__init__(self, name=name, args=(self.condition,))
        Sprite.__init__(self)
        self.name = name

    def change(self, color: Color = None):
        self.set_light(color)

    def set_light(self, color: Color):
        self.current_light = color
        src = r"D:\\PRACTICE\\conc_p_py\\resources\\%s-%s.png" % (str(self.direction.value).lower(), str(color.value).lower())
        self.image = pygame.image.load(src).convert_alpha()

    def __str__(self) -> str:
        return "%s: %s" % (self.name, str(self.current_light))

    # Thread get condition then check if meet requirments -> green light car can go -> red light sleep -> statement: wait 
    def run(self):
        with self.condition:
            while True:
                self.condition.acquire()
                self.change(Color.GREEN)
                sleep(self.context.velocity)
                self.change(Color.YELLOW)
                sleep(self.context.velocity * .05)
                self.change(Color.RED)
                self.condition.wait()

    def stop(self):
        # delays a execution until the target thread has been completely read.
        self.join()

    def update(self):
        Sprite.update(self)


class Vehicle(Sprite):
    def __init__(self, src: str, start_position: tuple = (0, 0), direction: tuple = (0, 0),
                 context: Context = None, semaphore: Semaphore = None):
        Sprite.__init__(self)
        self.start_position = start_position
        self.position = pygame.math.Vector2(start_position)
        self.dir = pygame.math.Vector2(direction).normalize()
        self.image = pygame.image.load(src).convert_alpha()
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect(center=start_position)
        self.context = context
        self.semaphore = semaphore
        self.stop = False
    
    # update new car those go beyong the map 
    def update(self):
        if (self.start_position[0] > 528 and self.rect.x < 0) \
                or (self.start_position[0] < 0 and self.rect.x > 528) \
                or (self.start_position[1] < 0 and self.rect.y > 528) \
                or (self.start_position[1] > 528 and self.rect.y < 0):
            self.position = (self.start_position[0], self.start_position[1])
        
        #check collide : red light & collide  reach traffic light area -> stop
        if self.semaphore.current_light == Color.RED and self.semaphore.crosswalk.colliderect(self.rect):
            return

        self.position += self.dir * self.context.velocity
        self.rect.center = (self.position.x, self.position.y)

    """
    The processing flow is as follows:
    First acquire a condition variable, and then judge some conditions.
    wait if the condition is not met,
    
    If the conditions are met, after some processing is performed to change the conditions, other threads are notified through the notify method, and other threads in the wait state will re-evaluate the conditions after receiving the notification.
    This process is repeated continuously to solve complex synchronization problems.
    It can be considered that the Condition object maintains a lock (Lock/RLock) and a waiting pool. The thread obtains the Condition object through acquire. When the wait method is called, the thread will release the lock inside the Condition and enter the blocked state.
    
    At the same time, record this thread in the waiting pool. When the notify method is called, the Condition object will pick a thread from the waiting pool and notify it to call the acquire method to try to acquire the lock.

    The constructor of the Condition object can accept a Lock/RLock object as a parameter. If not specified, the Condition object will create an RLock internally.

    In addition to the notify method, the Condition object also provides the notifyAll method, which can notify all threads in the waiting pool to try to acquire the internal lock. Due to the above mechanism, threads in the waiting state can only be woken up by the notify method,
    So the function of notifyAll is to prevent some threads from being silent forever.

     """
    
# get arg thread
class Manager(Thread):

    
    def __init__(self, condition: Condition = Condition(), context: Context = None):
        self.condition = condition
        self.is_running = True
        self.context = context
        super().__init__(name="manager", args=(self.condition,))

    def run(self):
        with self.condition:
            while self.is_running:
                # acquire rlock
                self.condition.acquire()
                # notify all thread which statement is wait ,chose thread change it statement to acquire 
                self.condition.notifyAll()
                # release lock self wait 
                self.condition.wait(self.context.velocity)

    def stop(self):
        self.is_running = False
        # delays a program's flow of execution until the target thread has been completely read.
        self.join()


   


def main():
    # Init
    pygame.init()
    screen = pygame.display.set_mode((520, 520))
    clock = pygame.time.Clock()
    program_icon = pygame.image.load('D:\PRACTICE\\conc_p_py\\resources\icon.png')
    pygame.display.set_icon(program_icon)
    running = True

    # Headless process
    condition = Condition()
    context = Context()
    # range area of semaphore                     
    rect_south = pygame.Rect(120, 120, 60, 20)
    rect_north = pygame.Rect(200, 220,120, 20)
    rect_west = pygame.Rect(240, 150, 40, 120)
    rect_east = pygame.Rect(120, 200, 20, 120)

    manager = Manager(condition=condition, context=context)
    #traffic light location
    semaphore_north = Semaphore(name="semaphore1", condition=condition, context=context, position=(275, 280),
                                direction=Direction.NORTH, color=Color.RED, crosswalk=rect_north)
    semaphore_south = Semaphore(name="semaphore2", condition=condition, context=context, position=(140, 130),
                                direction=Direction.SOUTH, color=Color.RED, crosswalk=rect_south)
    semaphore_east = Semaphore(name="semaphore3", condition=condition, context=context, position=(140, 280),
                               direction=Direction.EAST, color=Color.RED, crosswalk=rect_east)
    semaphore_west = Semaphore(name="semaphore4", condition=condition, context=context, position=(275, 130),
                               direction=Direction.WEST, color=Color.RED, crosswalk=rect_west)

    semaphore_north.start()
    semaphore_south.start()
    semaphore_east.start()
    semaphore_west.start()

    manager.start()

    # Animations  car starts in different position (650, 131) (-48, 200) (170, -32) (250, 560)
    horizontal_UP = Vehicle(src=r'D:\\PRACTICE\\conc_p_py\\resources\\horizontal_up.png', start_position=(650, 131),
                                   direction=(-1, 0), context=context, semaphore=semaphore_west)
    
    horizontal_DOWN = Vehicle(src=r'D:\\PRACTICE\\conc_p_py\\resources\\horizontal_down.png', start_position=(-48, 200),
                                  direction=(1, 0), context=context, semaphore=semaphore_east)
    
    vertical_LEFT = Vehicle(src=r'D:\\PRACTICE\\conc_p_py\\resources\\vertival_left.png', start_position=(170, -32),
                                     direction=(0, 1), context=context, semaphore=semaphore_south)
   
    vertical_RIGHT = Vehicle(src=r'D:\\PRACTICE\\conc_p_py\\resources\\vertival_right.png', start_position=(250, 560),
                                     direction=(0, -1), context=context, semaphore=semaphore_north)

    map = Map(context=context)

    group_general = Group(map)
    group_semaphores = Group(semaphore_north, semaphore_south, semaphore_east, semaphore_west)
    group_vehicles = Group([
        horizontal_UP,
        horizontal_DOWN,
        vertical_LEFT,
        vertical_RIGHT,])



    while running:
        clock.tick(30)

        group_vehicles.update()
        group_semaphores.update()

        events = pygame.event.get()

        for event in events:
            if event.type == pygame.MOUSEBUTTONUP:
                print(event.pos)   
            if event.type == pygame.QUIT:
                running = False

        screen.fill(BACKGROUND_COLOR)

        group_general.draw(screen)
        group_semaphores.draw(screen)
        group_vehicles.draw(screen)


        pygame.display.update()
        pygame.display.flip()

    pygame.quit()


if __name__ == '__main__':
    main()
