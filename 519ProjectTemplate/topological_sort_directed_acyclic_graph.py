from eva import EvaProgram, Input, Output, evaluate
from eva.ckks import CKKSCompiler
from eva.seal import generate_keys
from eva.metric import valuation_mse
import timeit
import networkx as nx
from random import random
from os import mkdir

# Helper packages
import matplotlib.pyplot as plt

# Using networkx, generate a random directed acyclic graph
def generateGraph(n, prob):
    G = nx.gnp_random_graph(n, prob, directed=True)
    nodes = [(u,v) for (u,v) in G.edges() if u<v]
    DAG = nx.DiGraph(nodes)

    print("nodes:", nodes)
    # print("DAG.nodes():", DAG.nodes())
    # print("list(nx.topological_sort(DAG)):", list(nx.topological_sort(DAG)))
    # print("list(nx.all_topological_sorts(DAG)):", list(nx.all_topological_sorts(DAG)))
    print("nx.is_directed_acyclic_graph(DAG):", nx.is_directed_acyclic_graph(DAG))

    plt.tight_layout()
    nx.draw_networkx(DAG, arrows=True)
    # plt.show()
    plt.savefig("results/DAG.png", format="PNG")
    # tell matplotlib you're done with the plot: https://stackoverflow.com/questions/741877/how-do-i-tell-matplotlib-that-i-am-done-with-a-plot
    plt.clf()

    return DAG, nodes

# If there is an edge between two vertices its weight is 1 otherwise it is zero
# Two dimensional adjacency matrix is represented as a vector
# Assume there are n vertices
# (i,j)th element of the adjacency matrix corresponds to (i*n + j)th element in the vector representations
def serializeGraphZeroOne(GG,vec_size):
    # n = GG.size()
    n = len(GG.nodes())
    print("n:", n)
    graphdict = {}
    g = []
    for row in range(n):
        for column in range(n):
            if GG.has_edge(row, column):
                weight = 1
            else:
                weight = 0 
            g.append(weight)  
            key = str(row)+'-'+str(column)
            graphdict[key] = [weight] # EVA requires str:listoffloat
    
    print("g:", g)
    print("len(g):", len(g))
    
    # EVA vector size has to be large, if the vector representation of the graph is smaller, fill the eva vector with zeros
    for i in range(vec_size - n*n):
        g.append(0.0)
    print("len(g):", len(g))
    return g, graphdict

# To display the generated graph
def printGraph(graph,n):
    for row in range(n):
        for column in range(n):
            print("{:.5f}".format(graph[row*n+column]), end = '\t')
        print() 

# Eva requires special input, this function prepares the eva input
# Eva will then encrypt them
def prepareInput(n, vec_size):
    input = {}
    GG, nodes = generateGraph(n, 0.5)

    in_degree = [0] * n
    for (src, dest) in nodes:
        in_degree[dest] += 1
    print("in_degree:", in_degree)
    for i in range(vec_size-n):
        in_degree.append(0)

    discovered = []
    for i in range(vec_size):
        discovered.append(0)
        
    # graph is a list
    graph, graphdict = serializeGraphZeroOne(GG, vec_size)
    input['Graph'] = graph
    return input, in_degree, discovered

# This is the dummy analytic service
# You will implement this service based on your selected algorithm
# TODO: you can other parameters using global variables !!! do not change the signature of this function
# Size of parameters are equal but graph has n^2 elements and in_degree n
def graphanalticprogram(graph, in_degree, discovered, path, n):
    first_one = []
    for i in range(len(in_degree)):
        first_one.append(0)
    first_one[0] = 1
    state = "calculate"
    if state == "calculate":
        
        pass
    
    reval = graph<<2 ## Check what kind of operators are there in EVA, this is left shift
    print(graph)
    for i in range(n):
        # They are compute helpers and can be compared
        if in_degree[i] == 0 and not discovered[i]:
            # n block shifted to far left
            n_block = graph << (i*n)
            for k in range(n):
                f = n_block << k
                print(f * first_one)
                # if(f * first_one)
                # if f * 


    # print("graphanalticprogram")
    # print("reval")
    # print(reval)
    # print("graph")
    # print(graph)
    # Note that you cannot compute everything using EVA/CKKS
    # For instance, comparison is not possible
    # You can add, subtract, multiply, negate, shift right/left
    # You will have to implement an interface with the trusted entity for comparison (send back the encrypted values, push the trusted entity to compare and get the comparison output)
    # return graph
    
    return graph * first_one
    
# Do not change this 
# the parameter n can be passed in the call from simulate function
class EvaProgramDriver(EvaProgram):
    def __init__(self, name, vec_size=4096, n=4):
        self.n = n
        super().__init__(name, vec_size)

    def __enter__(self):
        super().__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        super().__exit__(exc_type, exc_value, traceback)

# Repeat the experiments and show averages with confidence intervals
# You can modify the input parameters
# n is the number of nodes in your graph
# If you require additional parameters, add them
def simulate(n):
    m = 4096*4
    print("Will start simulation for ", n)
    config = {}
    config['warn_vec_size'] = 'false'
    config['lazy_relinearize'] = 'true'
    config['rescaler'] = 'always'
    config['balance_reductions'] = 'true'
    inputs, in_degree, discovered = prepareInput(n, m)
    # print(in_degree)

    graphanaltic = EvaProgramDriver("graphanaltic", vec_size=m,n=n)
    with graphanaltic:
        # Graph adjacency list is private information, therefore we will encrpyt it
        # In degree and discovered lists are computational helpers and they are not encrypted.
        graph = Input('Graph') # Encrypted input

        reval = graphanalticprogram(graph, in_degree, discovered, n)
        Output('ReturnedValue', reval)
    
    prog = graphanaltic
    prog.set_output_ranges(30)
    prog.set_input_scales(30)

    compiler = CKKSCompiler(config=config)
    compiled_multfunc, params, signature = compiler.compile(prog)
    public_ctx, secret_ctx = generate_keys(params)
    encInputs = public_ctx.encrypt(inputs, signature)
    encOutputs = public_ctx.execute(compiled_multfunc, encInputs)
    outputs = secret_ctx.decrypt(encOutputs, signature)
    reference = evaluate(compiled_multfunc, inputs)
    
    # Change this if you want to output something or comment out the two lines below
    # print(outputs)
    for key in outputs:
        # print(key, outputs[key][:n*n], reference[key][:n*n])
        print(key, [int(i) for i in reference[key][:n*n]])

    mse = valuation_mse(outputs, reference) # since CKKS does approximate computations, this is an important measure that depicts the amount of error

    return mse


if __name__ == "__main__":
    bm_keys = ["NodeCount","PathLength","CompileTime","KeyGenerationTime","EncryptionTime","ExecutionTime","DecryptionTime","ReferenceExecutionTime","Mse"]

    simcnt = 1 #The number of simulation runs, set it to 3 during development otherwise you will wait for a long time
    
    try:
        mkdir("results")
    except:
        pass

    resultfile = open("results/results.csv", "w")  # Measurement results are collated in this file for you to plot later on
    resultfile.write(",".join(bm_keys) + "\n")
    resultfile.close()
    
    print("Simulation campaing started:")
    nodes = []
    n = 10
    resultfile = open("results/results.csv", "a")

    for i in range(simcnt):
        #Call the simulator
        mse = simulate(n)
        res = str(mse) + "\n"
        print("Result:", res)
        resultfile.write(res)

    resultfile.close()

    # for nc in range(36,64,4): # Node counts for experimenting various graph sizes
    #     n = nc
    #     resultfile = open("results/results.csv", "a")

    #     for i in range(simcnt):
    #         #Call the simulator
    #         mse = simulate(n)
    #         res = str(mse) + "\n"
    #         print("Result:", res)
    #         resultfile.write(res)

    #     resultfile.close()