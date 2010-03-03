#include <time.h>
#include <Python.h>
#include <timefuncs.h>

struct timeval t;


typedef struct tag1 {
	double ft; // time
	long diff;
	struct tag1 *next;
} speedstack_item;

typedef struct {
	long current;
	short int stacklen;
	double updateinterval;
	double speedlimit;
	double speedlimit_lastupdate;
	long speedlimit_lastcurrent;
	struct tag1 *stack_head, *stack_tail;
	long verbose;
} speedstack;

static double
floattime(void)
{
	gettimeofday(&t, NULL);
	return (double)t.tv_sec + t.tv_usec*0.000001;
}

static void
speedstack_destroy(void *ssptr)
{
	speedstack *ss = (speedstack *) ssptr;
	speedstack_item *curr, *next;
	
	curr = ss->stack_head;
	while (curr) {
		next = curr->next;
		free(curr);
		curr = next;
	}

	free(ss);
}




static PyObject *
speedstack_create(PyObject *self, PyObject *args)
{
	speedstack *ss = malloc(sizeof(speedstack));
	
	PyArg_ParseTuple(args, "dd", &ss->speedlimit, &ss->updateinterval);
	ss->stacklen = 0;
	ss->stack_head = ss->stack_tail = NULL;
	ss->speedlimit_lastupdate = 0.0;
	ss->speedlimit_lastcurrent = 0;

	return PyCObject_FromVoidPtr(ss, speedstack_destroy);
}



static PyObject *
speedstack_update(PyObject *self, PyObject *args)
{
	speedstack_item *si;
	long current; unsigned short int force; void *sspyco;
	PyArg_ParseTuple(args, "OlH", &sspyco, &current, &force);
	speedstack *ss = (speedstack *) PyCObject_AsVoidPtr(sspyco);
	
	double now = floattime();

	if (ss->stacklen == 0) {
		si = malloc(sizeof(speedstack_item));
		si->ft = now;
		si->next = NULL;
		si->diff = 0;
		ss->stack_head = ss->stack_tail = si;
		ss->stacklen++;
		ss->current = ss->speedlimit_lastcurrent = current;
		ss->speedlimit_lastupdate = now;
		return Py_BuildValue("");
	}


	// perform delay
	if (ss->speedlimit) {
		double timediff = now - ss->speedlimit_lastupdate;
		double bytediff = (double) (current - ss->speedlimit_lastcurrent);
		double delay = (bytediff / ss->speedlimit) - timediff;
		if (0.0 < delay) {
			t.tv_sec = (long) floor(delay);
			t.tv_usec = (long) (fmod(delay, 1.0)*1000000.0);
			select(0, (fd_set *)0, (fd_set *)0, (fd_set *)0, &t);
		}
		now = floattime();
	}



	
	if ( (now - ss->stack_tail->ft) < ss->updateinterval && !force)
		return Py_BuildValue("");


	si = malloc(sizeof(speedstack_item));
	si->ft = now;
	si->next = NULL;
	si->diff = current - ss->current;
	ss->current = current;
	ss->stack_tail = ss->stack_tail->next = si;
	ss->stacklen++;
	
	if (ss->stacklen > 100 || 2.0 < ss->stack_tail->ft - ss->stack_head->ft) {
		si = ss->stack_head;
		ss->stack_head = si->next;
		free(si);
		ss->stacklen--;
	}

	// calculate the speed
	double speed = 0.0;
	si = ss->stack_head;
	while (si->next) {
		speed += si->next->diff;
		si = si->next;
	}
	speed /= (ss->stack_tail->ft - ss->stack_head->ft);
	

	return PyFloat_FromDouble(speed);
}




static PyMethodDef Methods[] = {
	{"create", speedstack_create, METH_VARARGS, "Create speed stack data stucture"},
	{"update", speedstack_update, METH_VARARGS, "Add data to the speed stack and get transfer speed back"}
};

PyMODINIT_FUNC initspeedstack(void)
{
	(void) Py_InitModule("speedstack", Methods);
}


