# Project Information

This is the dockerfile for generating a container that establishes the development environment for CENG519. The required packages (Microsoft SEAL and EVA) are already installed. Networkx is also installed for graph generation. You will implement a graph algorithm preserving the privacy of the graph. Note that, CKKS used by EVA is not powerful enough to do all kinds of computations. There is no comparison for instance. 

# Running the example
```
python3 519ProjectTemplate/fhe_template_project.py
```

In this work, a secure implementation of topological sort of a DAG
(Directed Acyclic Graph) is implemented between a server and client
using homomorphic encryption. The system is built on a mock
client-server architecture where client encrypts a list representation
of a DAG using Microsoft SEAL library, and server makes computational
operations on encrypted data. The operations that can run on encrypted
data are limited, hence the more complicated operations need to be
dissembled to more basic operations, making the implementation
challenging. The operations that can neither be simplified nor available
are instead sent back to client, which returns the outcome to server.
This results in a slow solution; but ensures that the data is not
decrypted at the server.

Introduction
============

Encryption of data is usually relevant for storing or transportation
stages of data. This is partially because traditional cryptography
techniques require the data to be unencrypted to be able to process it
correctly, which implies that at some stage on a supposedly secure
system, the data has to be decrypted and processed in plaintext.
Examples to this situation are; sensitive information of companies being
processed by 3rd parties, or data analytics extracted from personal
data, and other situations where the data is entrusted with the hope
that is won't be misused or get stolen [@keyfactor].\


\
A viable solution to this problem Homomorphic encryption. In principle,
the term \"homomorphic encryption\" generalises encryption techniques
that \"allow encrypted data to be processed as if it were in plaintext
and produce the correct value once decrypted\"  [@Oreilly1]. However, in
order to keep the data safe, the operations that server can run on
encrypted data are need to be limited. Currently there are three types
of homomorphic encryption scheme that is categorized by the operations
they provide  [@keyfactor]:

1.  Partially homomorphic encryption: only one mathematical operation
    can be performed an unlimited number of times on the encrypted data.

2.  Somewhat homomorphic encryption: any number of additions but only
    one multiplication operation can be performed on the encrypted data.

3.  Fully homomorphic encryption: any number of additions and
    multiplications operation can be performed on the encrypted data.

\
While these limitations help prevent unauthorized decryption,
implementing the algorithms that will process the data becomes
challenging. The technique demonstrated in this project is fully
homomorphic encryption. A major data representation and processing model
makes use of Graph Theory; therefore we implement Topological Sorting on
Directed Acyclic Graphs using fully homomorphic encryption. The
encryption algorithm is provided by Microsoft SEAL library
 [@MicrosoftSeal].

Background and Related Work
===========================

Background
----------

The project requires prerequisites on graph theory, programming with
Python and general knowledge of server-client architecture.

Related Work
------------

While homomorphic encryption is not a new technique, it is still not
very wide-spread, resulting in scarce related work.\
\
Some libraries that are currently available are:

1.  A fully homomorphic encryption library is PALISADE  [@palisade]

2.  awesome-he by jonaschn  [@he_awesome-he]

3.  fully-homomorphic-encryption by Google  [@he_google]

4.  TFHE: Fast Fully Homomorphic Encryption over the Torus  [@he_thfe]

Microsoft SEAL is considered \"leveled fully homomorphic\" by some
sources [@he_wiki]

\

Main Contributions
==================

Implementation of Comparison
----------------------------

The algorithm to be implemented is a graph sorting algorithm, and it
requires comparisons on data in regular domain. However fully
homomorphic encryption provides limited operations: the Microsoft SEAL
library which is the backbone of the encryption system does not allow
comparison operations. This problem is solved by introducing a mechanism
between the server and the client to provide comparison operation.

Since the comparison operation is not an option in the encrypted data on
the server side, an interface with the client is implemented. This
interface should allow client to be invoked from the server, and it
should allow the server to continue the processing from where it left
off. In other words, the comparison operation is temporarily handed back
to client to make up for the limited availability of mathematical
operations on server side.

Client-Server Interface
-----------------------

The need for such an interface is required because the server can not
handle the comparison. This interface should satisfy two fundamental
flows besides comparison implementation:

1.  Server should invoke the client whenever necessary and the client
    should be able to handle this interrupt.

2.  After client is processed the data and invoke the server, server
    should run from where it left of.

Also the data to be compare should be managed in the server. That means
instead of sending data, use multiplication with an array that includes
only one 1 and the other items are zero. That results with an array that
either all zero or has only one item equals to 1. Therefore index can be
detected but data itself can not be accessed.

Methodology
===========

The code simulates the selected algorithm securely. When it runs, it
automatically creates a DAG with selected node size and makes operations
on this graph. After resulting with the simulation, it generates results
file, plots figures and, draws a visual representation of the graph. The
code can be seen in Appendix C.

Server Implementation
---------------------

The server -which is represented by a function- should implement the
selected algorithm: Kahn's Algorithm for Topological Sorting [@khans].
As stated on previous sections the limitations should be handled by the
server by implementing client-server interface. To satisfy the
requirement of client-server interface, following features should be
added to server code:

1.  Server should hold a state. The state is also the main communication
    mechanism between client and the server.

2.  Server should yield a state-result pair instead of returning.
    Yielding provides both invoking the client and the resuming from
    yield location.

Server is implemented in such a manner that the only encrypted data is
the graph itself. The helper variables such as in-degree array and state
of the process is held in global scope. Therefore they are not
protected. The reason behind that is keeping the encryption operations
simple as possible due to scope of the assignment. But all of the
operations can also be applied the helper variables.

There are two types of states that server provides:

1.  State \"check if all zero\": It is yielded with an encrypted array
    that has either all of its items are zero or only the first item is
    one

2.  State \"finished\": Sent when the sorting operation is completed.

When the only incoming states which is \"not all zero\" is set by the
client, server knows comparison returns true.

### Kahn's Algorithm for Topological Sorting

Once all the required mathematical operations are provided either by the
encryption library or via client-server communication; Kahn's algorithm
for topological sorting can be implemented by executing the following
steps:

1.  Compute in-degree (number of incoming edges) for each of the node.

2.  Pick all the nodes with in-degree as 0 and add them into a queue:
    This operation requires comparing in-degree items with 0.

3.  Pop a node from the queue.

4.  Decrease in-degree by 1 for all its neighbouring nodes. If in-degree
    of a neighbouring node is reduced to zero, then add it to the queue:
    This operations requires finding neighbours which includes
    comparison operation.

5.  Repeat Step 3 until the queue is empty.

Client Implementation
---------------------

The client is responsible for providing graph and necessary helper
variables stated in the server implementation section. Also it should
handle the basic requests from the server by using client-server
interface. To satisfy the requirement of client-server interface,
following features should be added to client code:

1.  Since the server yields results, the client should iterate the
    server by calling next on the generator function of the server.

2.  For every iteration, client should check the state in the response
    from server and act according to it.

The incoming states is handled as follows:

1.  State \"check if all zero\": This state means that server needs a
    comparison operation. The resulting array will be decrypted by the
    client and content will be checked if all the items are zero or not.
    If the all items are not zero, client will set global state to \"not
    all zero\" and iterate the server.

2.  State \"finished\": This state means sorting operation is completed
    and the result is achieved.

Development Environment
-----------------------

The building and running environment is Ubuntu Linux that runs on a
Docker container. The related Dockerfile can be seen in Appendix A.
Microsoft SEAL encryption library used as the core of the homomorphic
encryption. The mock server-client architecture is implemented using
Python programming language on Visual Studio Code editor.

Results and Discussion
======================

Results
-------

As we can see in the selected graph, there is a linear
relationship between resources consumed and the node count. The pitfalls
represent that algorithm is failed to find a topological sort, therefore
run time is decreased at that points. 

Discussion
----------

The results can be observed from two different perspectives. First of
them is the correctness of the results and the other is efficiency of
the algorithm. Correctness of the algorithm is verified by network
library functions and it is seen that results are not correct sometimes.
The pitfall in the graphs shows that algorithm is failed and therefore
run time is slow. Efficiency of the algorithm, on the other hand, should
be increased. Because the data is transmitted between server and the
client multiple times for only one operation, a huge overhead is
included in the system. The graph that shows total time required by the
node count below shows that.

Conclusion
==========

The project is developed as a proof-of-concept work. That means only the
graph data itself is encrypted, not the other variables. Therefore there
are several security vulnerabilities. The helper variables that are not
encrypted can be observed and the data becomes a subject to reverse
engineering. Also the global state can be tracked to observe the current
state of server. The final output is not also encrypted because of
simplicity. To overcome such an important issue all of the variables can
be encrypted alongside with the graph and necessary functions can be
implemented in the client-server interface if can not be implemented in
the server. Also such algorithms can be designed to eliminate the extra
data transfer between server and the client.
