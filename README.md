

<!-- GENERATED README FILE. DO NOT EDIT.    -->
<!-- source in worm-assignment-text/        -->

# Mandatory Assignment 2: The Worm

UiT INF-3203, Spring 2021 \
Mike Murphy and Otto Anshus


**Due date: Friday April 16th at 10:15**

## Contents

  - [Worm Assignment Overview](#worm-assignment-overview)
  - [General Requirements](#general-requirements)
  - [Worm Operation](#worm-operation)
      - [Cluster Review](#cluster-review)
      - [Worm Gate API Overview](#worm-gate-api-overview)
      - [Worm Constraints](#worm-constraints)
  - [Worm Evaluation](#worm-evaluation)
  - [Delivery](#delivery)
      - [Source Code](#source-code)
      - [Report](#report)
      - [Demo](#demo)
  - [References](#bibliography)

## Also in This Repository

- [`worm_gate/`](worm_gate/) --- Code for the worm gates
- [`python_zip_example/`](python_zip_example/) --- An example
    of how to package a Python program to run in the worm gate

## Worm Assignment Overview

Your assignment will be to create a distributed program that stays alive
in the face of failures. This program will be in the form of a *worm*.

Computer worms were an early and influential experiment in distributed
computation, first described in a 1982 paper by John F. Soch and Jon A.
Hupp at the Xerox Palo Alto Research Center \[[1](#ref-shoch1982Worm)\].
A worm is a distributed program, where each process running on a
separate network node is called a worm *segment*. The segments of the
worm communicate to perform some cooperative computation, the *payload*.
And if a segment dies, the worm will compensate by creating a new
segment and migrating to a new node. Thus, it can stay alive on the
network even if nodes or segments fail.

A worm enters nodes via a mechanism called the *worm gate*, which
receives and starts the worm segment code. (For a malicious worm the
worm gate could be a security hole in other software. Or, for benevolent
worms, the worm gate can be a server specifically for enabling worms.)

In this assignment, you will write a worm to run on our development
cluster, `uvcluster`. The *worm gates* will be servers that we provide
that have an API for uploading and running code. Everything else is up
to you.

Your worm must stay alive in the face of node or network failures, and
you should have some kind of mechanism to query its status or have it
report its status to some “home base.”

Your worm must include some mechanism to shut itself down. Robert Morris
may be an assistant professor at MIT now \[[2](#ref-morrisCsail)\] (and
one of the coauthors of the Chord paper \[[3](#ref-chord)\]), but he got
in a lot of trouble as a grad student in 1988 when a worm he created got
out of control and crippled the early internet
\[[4](#ref-morrisCase)\]–\[[6](#ref-orman2003MorrisWormFifteenYears)\].

## General Requirements

You should continue to work in your groups from the presentations and
assignment 1.

The worm-gate server code is written in Python, but you are welcome to
implement the worm in any language that can run on the cluster. It is
allowed to use pre-written libraries as long as you can package them
with your worm segment code to upload to the worm gates.

## Worm Operation

You will start the provided worm gate server on multiple nodes in the
cluster, then you will run your worm via those worm gates. Remember that
you can run multiple worm gates per node by varying the port numbers.

Your worm must use the worm-gate’s upload mechanism to spread from node
to node to grow to a target size. You should be able to query its status
and/or have its status reported to you.

If your worm is not at its target size, it must either grow or shrink to
the target size. The worm should measure the time between noticing that
it is the wrong size to the time that it becomes stable at the target
size. And you should be able to query this measurement or have it sent
to a “home base” that you control.

The worm gate can and will kill your worm segments. The worm should
notice that a segment is down and adjust its size as described above.
Worm gates may also stop cooperating and refuse requests to run worm
code.

<!--
In order to be able to simulate network failures, the worm gate will
have an API to list "reachable" nodes. This list will change at run
time, and your worm must consult this list every time that it wants to
send a network message, before sending the message. If the target
recipient is not on the list, you may not send that message.
-->

Having a well-behaved worm will require communication and shared state
between segments. More importantly, this will require some kind of
coordination or consensus between segments. You are encouraged to use a
known consensus algorithm such as
Paxos \[[7](#ref-lamport2001PaxosMadeSimple)\],
\[[8](#ref-vanRenesse2015PaxosModeratelyComplex)\] or Raft
\[[9](#ref-ongaro2014Raft)\] for coordination. You may use pre-written
libraries.

### Cluster Review

The cluster front-end server is `uvcluster.cs.uit.no`. Your user logins
from last semester have been reset, but you should have received an
email a few weeks ago with new login information. If you do not have a
login or your does not work, email Mike and we will get you set up.

Note that due to the increased cybersecurity protections that went into
effect early this year, the cluster can only be accessed via UiT’s
network or VPN.

Worm gates and segments should be run on the cluster’s compute nodes,
not the frontend. Remember that you can run multiple servers on the same
compute node by varying the port numbers.

See the cluster info document for more information on the cluster
itself.

### Worm Gate API Overview

The worm gate will have a RESTful HTTP API with the following
capabilities:

  - **info**: get info about this worm gate  
    (including a list of neighbor gates to spread to)
  - **entrance**: upload and start worm segment code
  - **kill**: kill any worm segments running via this gate

See the README file in the worm gate code for API details.

Your worm segments may communicate between themselves however they like,
but you should remain in control of your worm at all times. You must be
able to shut it down.

### Worm Constraints

The worm must operate within the following constraints:

  - The number of running worm segments must stay close to the target.
    (Some margin of error or delay is allowed, but the worm must not
    grow out of control.)

  - Worm state data must be kept in RAM. (No using the disk.)

  - The worm must use the provided worm-gate upload-and-run mechanism to
    move from node to node. (Absolutely no use of SSH or the shared
    `/home` directory.)

  - Assume that running segments can fail (or be killed). The worm as a
    whole should still survive. However, **the worm must shut down when
    ordered to**.

<!--
-   The worm must consult the worm gate's list of "reachable" nodes
    before every network message that it sends. If the destination is
    not on the list, the worm may not send that message.
-->

## Worm Evaluation

You must perform the following experiments to measure the following
metrics for your worm:

1.  **Time to grow from 1 to 𝑛 segments,** 𝑛 = 2…20
    
    Your worm will naturally start as a single segment. As stated in the
    operation section, it should grow to its target size and report the
    time that it took to grow and stabilize. You must repeat this
    experiment, varying the target size 𝑛 from 2 to 20 and record the
    result of each trial. You are encouraged to also experiment with
    larger worms, but trials from 2 to 20 are required.
    
    How you determine that the worm is stable is up to you.

2.  **Time for worm of size 𝑛 to recover from 𝑘 segments killed,**
    𝑛 = 10, 𝑘 = 1…9
    
    Start with a worm of size 𝑛 = 10 and send commands to some 𝑘 worm
    gates to kill the segments they are hosting. The worm should notice
    the missing segments, correct back to its target size, and report
    elapsed time. Repeat this experiment, increasing the number of
    segments killed 𝑘 from 1 to 9 and record the results. You may choose
    to perform this experiment with a larger worm, but 10 is the minimum
    size.

Your report should include a plot with the results of each experiment,
as well as discussion of the results.

You should perform multiple trials (at least 3) for each independent
variable, and plot the data with error bars.

Note that short stabilization times are not necessarily the goal here.
You will not be penalized for having a slow worm. The goal is to
increase your insights into quantitatively evaluating what you build.

## Delivery

The delivery must include source code and report. You must also
participate in a demo session similar to the assignments last semester.

Source and report must be bundled together in a zip file or tarball and
uploaded to Canvas before the demo session. This means that the deadline
is during the day, before class, not midnight.

### Source Code

Your worm code:

  - must run on our cluster, `uvcluster.cs.uit.no`
  - may be in any language that runs on the cluster
  - must include a README file with instructions for running the code on
    the cluster

### Report

Your report should be 2–6 pages long, and it should follow the basic
structure of a scientific paper: title, author list, abstract,
introduction, architecture, design, experiments, results, discussion,
conclusion.

It should include the following:

  - A short introduction to computer worms.

  - A description of the architecture, design, and implementation of
    your worm. This should answer questions such as: What hardware and
    software is your worm running on? How do the segments communicate?
    What consensus algorithm do they use? What language is it
    implemented in? What libraries did you use? And why did you choose
    the design and implementation details that you did?

  - A description of your experiment methodology. Define your metrics.
    Answer questions such as: How exactly did you measure and report
    elapsed time? Did you use the `time` command, or a library within
    the worm segment code? What operating system or hardware mechanism
    underlies that command or library call? How did you determine when
    the worm had stabilized?

  - Plots of results for both experiments. Remember error bars on the
    plots.

  - Discussion of results.

We would also like to see some discussion on lessons learned while
implementing the worm. Did you have trouble controlling the worm? Did it
otherwise surprise you? Can you think of possible legitimate uses for a
benevolent worm? Or are they purely evil?

The report should be in PDF format, preferably typeset with LaTeX. Plots
should be in a vector-based format with axes clearly labeled. All
references should be properly cited.

### Demo

Like in INF-3200 last semester, you will be required to give an informal
demo where you briefly describe your solution and run your code on the
cluster. No slides are necessary, but be prepared to discuss your
solution and how it might differ from the solutions of other groups.
During the demo, Mike will be in control of the worm-gate servers that
will run your worm segment code, and they may include some surprises not
present in the code we hand out.

<!-- vim: set tw=72 : -->

# References

<div id="refs" class="references">

<div id="ref-shoch1982Worm">

\[1\] J. F. Shoch and J. A. Hupp, “The ‘worm’ programs—early experience
with a distributed computation,” *Commun. ACM*, vol. 25, no. 3, pp.
172–180, Mar. 1982, doi:
[10.1145/358453.358455](https://doi.org/10.1145/358453.358455).

</div>

<div id="ref-morrisCsail">

\[2\] MIT CSAIL, “Robert Morris: Professor.” Accessed: Mar. 04, 2020.
\[Online\]. Available: <https://www.csail.mit.edu/person/robert-morris>.

</div>

<div id="ref-chord">

\[3\] I. Stoica *et al.*, “Chord: A scalable peer-to-peer lookup
protocol for internet applications,” *IEEE/ACM Transactions on
Networking*, vol. 11, no. 1, pp. 17–32, 2003, doi:
[10.1109/TNET.2002.808407](https://doi.org/10.1109/TNET.2002.808407).

</div>

<div id="ref-morrisCase">

\[4\] United States Court of Appeals, Second Circuit, “United States vs.
Morris.” 1991, Accessed: Mar. 04, 2020. \[Online\]. Available:
<https://scholar.google.com/scholar_case?case=551386241451639668>.

</div>

<div id="ref-markoff1993ComputerIntruder">

\[5\] J. Markoff, “Computer intruder is put on probation and fined
$10,000,” *The New York Times*, May 1990, Accessed: Mar. 04, 2020.
\[Online\]. Available:
<https://www.nytimes.com/1990/05/05/us/computer-intruder-is-put-on-probation-and-fined-10000.html>.

</div>

<div id="ref-orman2003MorrisWormFifteenYears">

\[6\] H. Orman, “The Morris worm: A fifteen-year perspective,” *IEEE
Security Privacy*, vol. 1, no. 5, pp. 35–43, 2003, doi:
[10.1109/MSECP.2003.1236233](https://doi.org/10.1109/MSECP.2003.1236233).

</div>

<div id="ref-lamport2001PaxosMadeSimple">

\[7\] L. Lamport, “Paxos made simple,” pp. 51–58, 2001, \[Online\].
Available:
<https://www.microsoft.com/en-us/research/publication/paxos-made-simple/>.

</div>

<div id="ref-vanRenesse2015PaxosModeratelyComplex">

\[8\] R. Van Renesse and D. Altinbuken, “Paxos made moderately complex,”
*ACM Comput. Surv.*, vol. 47, no. 3, pp. 42:1–42:36, Feb. 2015, doi:
[10.1145/2673577](https://doi.org/10.1145/2673577).

</div>

<div id="ref-ongaro2014Raft">

\[9\] D. Ongaro and J. Ousterhout, “In search of an understandable
consensus algorithm,” in *2014 USENIX annual technical conference
(USENIX ATC 14)*, Jun. 2014, pp. 305–319, \[Online\]. Available:
<https://www.usenix.org/conference/atc14/technical-sessions/presentation/ongaro>.

</div>

</div>
