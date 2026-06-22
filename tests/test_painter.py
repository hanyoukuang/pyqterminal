import sys
import trace
import pty_demo

tracer = trace.Trace(count=False, trace=True, ignoredirs=[sys.prefix, sys.exec_prefix])
tracer.run('pty_demo.main()')
