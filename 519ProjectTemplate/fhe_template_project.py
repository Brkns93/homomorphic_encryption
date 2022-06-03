from itertools import tee
from termios import tcdrain
from eva import EvaProgram, Input, Output, evaluate
from eva.ckks import CKKSCompiler
from eva.seal import generate_keys
from eva.metric import valuation_mse
import timeit
import networkx as nx
from random import random
from os import mkdir
import copy

# Helper packages
import matplotlib.pyplot as plt

# Using networkx, generate a random directed acyclic graph
def generateGraph(n, prob):
    G = nx.gnp_random_graph(n, prob, directed=True)
    nodes = [(u,v) for (u,v) in G.edges() if u<v]
    DAG = nx.DiGraph(nodes)

    plt.tight_layout()
    nx.draw_networkx(DAG, arrows=True)
    plt.savefig(f"results/DAG_{n}.png", format="PNG")
    plt.clf()

    return DAG, nodes

# If there is an edge between two vertices its weight is 1 otherwise it is zero
# Two dimensional adjacency matrix is represented as a vector
# Assume there are n vertices
# (i,j)th element of the adjacency matrix corresponds to (i*n + j)th element in the vector representations
def serializeGraphZeroOne(GG,vec_size):
    n = len(GG.nodes())
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
    
    # EVA vector size has to be large, if the vector representation of the graph is smaller, fill the eva vector with zeros
    for i in range(vec_size - n*n):
        g.append(0.0)
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

    for i in range(vec_size-n):
        in_degree.append(0)
        
    # graph is a list
    graph, graphdict = serializeGraphZeroOne(GG, vec_size)
    input['Graph'] = graph
    return input, in_degree

global_state = "start"
global_in_degree = []
global_graph_size = 0
global_vector_size = 0

def graphanalticprogram(graph):
    global global_graph_size
    global global_vector_size
    global global_in_degree
    global global_state

    # Array for multiplication
    first_one = []
    for i in range(global_vector_size):
        first_one.append(0.0)
    first_one[0] = 1

    node_queue = []
    for i in range(global_graph_size):
        if global_in_degree[i] == 0:
            node_queue.append(i)

    top_order = []

    while node_queue:
        # Extract front of queue (or perform dequeue) and add it to topological order
        node_index = node_queue.pop(0)
        top_order.append(node_index)

        node_dest_block = graph << (node_index*global_graph_size) # Shifting
        for k in range(global_graph_size):
            current_dest = node_dest_block << k
            dest_exists_checker = current_dest * first_one # Multiplication
            global_state = "check_if_all_zero"
            
            yield global_state, dest_exists_checker # yielding!!!
            
            if global_state == "not_all_zero": # There is an edge from u to k
                global_in_degree[k] = global_in_degree[k] - 1
                if global_in_degree[k] == 0:
                    node_queue.append(k)
        
    yield "finished", top_order
    
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
    global global_state
    global global_in_degree
    global global_graph_size
    global global_vector_size

    results = {
        "Iterations": [],
    }

    m = 256

    print("Will start simulation for ", n)
    config = {}
    config['warn_vec_size'] = 'false'
    config['lazy_relinearize'] = 'true'
    config['rescaler'] = 'always'
    config['balance_reductions'] = 'true'
    inputs, global_in_degree = prepareInput(n, m)
    global_graph_size = n
    global_vector_size = m

    graphanaltic = EvaProgramDriver("graphanaltic", vec_size=m,n=n)
    with graphanaltic:
        
        total_start = timeit.default_timer()
        # Graph adjacency list is private information, therefore we will encrpyt it
        # In degree and discovered lists are computational helpers and they are not encrypted.
        graph = Input('Graph') # Encrypted input
        p = graphanalticprogram(graph)
        iter = 0
        prog = graphanaltic
        compiler = CKKSCompiler(config=config)
        while True:
            try:
                global_state, reval = next(p)
            except StopIteration as e:
                print("StopIteration exception occured. Breaking the loop...", e)
                break
            
            if global_state == "finished":
                print("Sorting is finished")
                print("Topological sort:", reval)
                break
            
            Output(f'ReturnedValue{iter}', reval)
            
            if global_state == "check_if_all_zero":
                result = {}
                prog.set_output_ranges(30)
                prog.set_input_scales(30)

                iter_start = timeit.default_timer()
                compiled_multfunc, params, signature = compiler.compile(prog)
                compiletime = (timeit.default_timer() - iter_start) * 1000.0 #ms
                result["CompileTime"] = compiletime
                
                iter_start = timeit.default_timer()
                public_ctx, secret_ctx = generate_keys(params)
                keygenerationtime = (timeit.default_timer() - iter_start) * 1000.0 #ms
                result["KeyGenerationTime"] = keygenerationtime
                
                iter_start = timeit.default_timer()
                encInputs = public_ctx.encrypt(inputs, signature)
                encryptiontime = (timeit.default_timer() - iter_start) * 1000.0 #ms
                result["EncryptionTime"] = encryptiontime

                iter_start = timeit.default_timer()
                encOutputs = public_ctx.execute(compiled_multfunc, encInputs)
                executiontime = (timeit.default_timer() - iter_start) * 1000.0 #ms
                result["ExecutionTime"] = executiontime

                iter_start = timeit.default_timer()
                outputs = secret_ctx.decrypt(encOutputs, signature)
                decryptiontime = (timeit.default_timer() - iter_start) * 1000.0 #ms
                result["DecryptionTime"] = decryptiontime

                iter_start = timeit.default_timer()
                reference = evaluate(compiled_multfunc, inputs)
                referenceexecutiontime = (timeit.default_timer() - iter_start) * 1000.0 #ms
                result["ReferenceExecutionTime"] = referenceexecutiontime
                
                if [k for k in reference[f'ReturnedValue{iter}'][:n*n] if k!=0]: # If not all zeros
                    global_state = "not_all_zero"
                else:
                    global_state = "all_zero"
            
                mse = valuation_mse(outputs, reference) # since CKKS does approximate computations, this is an important measure that depicts the amount of error
                result["Mse"] = mse

                results["Iterations"].append(result)
            iter += 1

    results["TotalTime"] = (timeit.default_timer() - total_start) * 1000.0 #ms
    return results


if __name__ == "__main__":
    total_results = []
    bm_keys = ["Sim#", "NodeCount","TotalIteration","CompileTime","KeyGenerationTime","EncryptionTime","ExecutionTime","DecryptionTime","ReferenceExecutionTime"]

    simcnt = 6 #The number of simulation runs, set it to 3 during development otherwise you will wait for a long time
    
    try:
        mkdir("results")
    except:
        pass

    resultfile = open("results/results.csv", "w")  # Measurement results are collated in this file for you to plot later on
    resultfile.write(",".join(bm_keys) + "\n")
    resultfile.close()
    
    print("Simulation campaing started:")
    for nc in range(6, 18, 4): # Node counts for experimenting various graph sizes
        n = nc
        resultfile = open("results/results.csv", "a")

        # Dict to hold the data to plot
        total_res = {}
        total_res["NodeCount"] = n
        total_res["CompileTime"] = []
        total_res["KeyGenerationTime"] = []
        total_res["EncryptionTime"] = []
        total_res["ExecutionTime"] = []
        total_res["DecryptionTime"] = []
        total_res["ReferenceExecutionTime"] = []

        for i in range(simcnt):
            total_res["CompileTime"].append(0)
            total_res["KeyGenerationTime"].append(0)
            total_res["EncryptionTime"].append(0)
            total_res["ExecutionTime"].append(0)
            total_res["DecryptionTime"].append(0)
            total_res["ReferenceExecutionTime"].append(0)
            
            #Call the simulator
            results = simulate(n)
            total_res["TotalTime"] = results["TotalTime"]
            iteration = 0
            for result in results["Iterations"]:
                iteration += 1
                total_res["CompileTime"][i] += result["CompileTime"]
                total_res["KeyGenerationTime"][i] += result["KeyGenerationTime"]
                total_res["EncryptionTime"][i] += result["EncryptionTime"]
                total_res["ExecutionTime"][i] += result["ExecutionTime"]
                total_res["DecryptionTime"][i] += result["DecryptionTime"]
                total_res["ReferenceExecutionTime"][i] += result["ReferenceExecutionTime"]
            
            csv_res = str(i) + "," + str(n) + "," + str(len(results["Iterations"])) + "," + str(total_res["CompileTime"][i]) + "," + str(total_res["KeyGenerationTime"][i]) + "," +  str(total_res["EncryptionTime"][i]) + "," +  str(total_res["ExecutionTime"][i]) + "," +  str(total_res["DecryptionTime"][i]) + "," +  str(total_res["ReferenceExecutionTime"][i]) + "\n"
            resultfile.write(csv_res)
        total_results.append(copy.deepcopy(total_res))

        resultfile.close()

    for key in [k for k in bm_keys if k not in ["Sim#", "NodeCount","TotalIteration", "Mse"]]:
        plt.cla()
        for res in total_results:
            if key in res:
                plt.plot(list(range(simcnt)), res[key], label = f"Node count {res['NodeCount']}")
        # plt.xlabel("PathLength")
        plt.ylabel(key)
        plt.title(key)
        plt.grid()
        plt.legend()
        plt.autoscale(enable=True, axis="y", tight=None)
        plt.savefig(f"results/{key}.png")
        # plt.show(block=False)