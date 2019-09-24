import asyncio, sys
#Following is the sample loop
queue = [
        Task(some_coroutine),
        Task(some_other_coroutine),
        ]

while queue:
    task = queue.pop(0)

    task.execute_coroutine()

    if task.is_coroutine_done():
        print('Finished task')
    else:
        queue.append(task)

print('Out of event loop')

#Quick Tour of API

#Creating a coroutine
async def some_coroutine():
    a = 1 + 2
    await asyncio.sleep(1)
    return a

#Running a coroutine
loop = asyncio.get_event_loop()

loop.run_until_complete(some_coroutine)#some_coroutine will be automatically get wrap in task

#Run multiple coroutine simultaneouly
#Make a wrapper function and call asyncio.gather and pass a tuple of functions to run simultaneously
async def sleep_a_lot():
    await asyncio.gather(*[some_coroutine() for i range(5)])
    print('Done')



