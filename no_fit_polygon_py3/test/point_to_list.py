pointA =[{'x': 3000, 'y': 1400}, {'x': 0, 'y': 1400}, {'x': 0, 'y': 0}, {'x': 3000, 'y': 0}]

pointB = [{'x': 1168.0, 'y': 2.0}, {'x': 2440.0, 'y': 2.0}, {'x': 2440.0, 'y': 668.0}, {'x': 1168.0, 'y': 668.0}]

new_pointA = [[p['x'], p['y']] for p in pointA]
new_pointB = [[p['x'], p['y']] for p in pointB]

print(new_pointA)
print(new_pointB)
