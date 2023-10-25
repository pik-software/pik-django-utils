def batched(value, chunk_size):
    for index in range(0, len(value), chunk_size):
        yield value[index:index + chunk_size]
