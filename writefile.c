#include <Python.h>

typedef struct {
	PyObject_HEAD
	int fd;
} FileWriteBuffer;

PyObject *
FileWriteBuffer_init(FileWriteBuffer *o, PyObject *args, PyObject *kwds)
{
	PyArg_ParseTuple(args, "i", &o->fd);
	return 0;
}


PyTypeObject FileWriteBufferType = {
	PyObject_HEAD_INIT(NULL)
    0,                                  /* ob_size */
    "pydl.FileWriteBuffer",               /* tp_name */
    sizeof(FileWriteBuffer),        /* tp_basicsize */
    0,                                  /* tp_itemsize */
    0,                                  /* tp_dealloc */
    0,                                  /* tp_print */
    0,                                  /* tp_getattr */
    0,                                  /* tp_setattr */
    0,                                  /* tp_compare */
    0,                                  /* tp_repr */
    0,                                  /* tp_as_number */
    0,                                  /* tp_as_sequence */
    0,                                  /* tp_as_mapping */
    0,                                  /* tp_hash */
    0,                                  /* tp_call */
    0,                                  /* tp_str */
    0,                                  /* tp_getattro */
    0,                                  /* tp_setattro */
    0,                                  /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT,                 /* tp_flags */
    0,                                  /* tp_doc */
    0,                                  /* tp_traverse */
    0,                                  /* tp_clear */
    0,                                  /* tp_richcompare */
    0,                                  /* tp_weaklistoffset */
    0,                                  /* tp_iter */
    0,                                  /* tp_iternext */
    0,              /* tp_methods */
    0,                                  /* tp_members */
    0,                                  /* tp_getset */
    0, /* &PycairoSurface_Type, */      /* tp_base */
    0,                                  /* tp_dict */
    0,                                  /* tp_descr_get */
    0,                                  /* tp_descr_set */
    0,                                  /* tp_dictoffset */
    (initproc)FileWriteBuffer_init,                                  /* tp_init */
    0,                                  /* tp_alloc */
    0,         /* tp_new */
    0,                                  /* tp_free */
    0,                                  /* tp_is_gc */
    0,                                  /* tp_bases */
};




PyMODINIT_FUNC
initFileWriteBuffer(void)
{
	PyObject* m;
	
	FileWriteBufferType.tp_new = PyType_GenericNew;

	if (PyType_Ready(&FileWriteBufferType) < 0)
		return;
	
	m = Py_InitModule3("FileWriteBuffer", NULL, "what am i doing here?");
	if (m == NULL)
		return;

	Py_INCREF(&FileWriteBufferType);
	PyModule_AddObject(m, "FileWriteBuffer", (PyObject *)&FileWriteBufferType);
}


