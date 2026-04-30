/****************************************************************************
**
** Copyright (C) 2017 The Qt Company Ltd.
** Contact: https://www.qt.io/licensing/
**
****************************************************************************/

(function() {
    "use strict";

    var QWebChannelMessageTypes = {
        Init: 0,
        Idle: 1,
        Debug: 2,
        Reply: 3,
        Signal: 4,
        Method: 5,
        PropertyUpdate: 6
    };

    var QWebChannel = function(transport, initCallback) {
        if (typeof transport !== "object" || typeof transport.send !== "function") {
            console.error("The QWebChannel transport object is invalid!");
            return;
        }

        var channel = this;
        this.transport = transport;

        this.send = function(data) {
            if (typeof data !== "string") {
                data = JSON.stringify(data);
            }
            channel.transport.send(data);
        };

        this.transport.onmessage = function(message) {
            var data = message.data;
            if (typeof data === "string") {
                data = JSON.parse(data);
            }
            switch (data.type) {
                case QWebChannelMessageTypes.Signal:
                    channel.handleSignal(data);
                    break;
                case QWebChannelMessageTypes.Response:
                    channel.handleResponse(data);
                    break;
                case QWebChannelMessageTypes.PropertyUpdate:
                    channel.handlePropertyUpdate(data);
                    break;
                default:
                    console.error("invalid message type received: ", data.type);
                    break;
            }
        };

        this.execCallbacks = {};
        this.execId = 0;
        this.exec = function(data, callback) {
            if (!callback) {
                channel.send(data);
                return;
            }
            var id = channel.execId++;
            channel.execCallbacks[id] = callback;
            data.id = id;
            channel.send(data);
        };

        this.objects = {};

        this.handleSignal = function(message) {
            var object = channel.objects[message.object];
            if (object) {
                object.signalEmitted(message.signal, message.args);
            } else {
                console.warn("Unhandled signal: " + message.object + "::" + message.signal);
            }
        };

        this.handleResponse = function(message) {
            if (!message.hasOwnProperty("id")) {
                console.error("Invalid response received: ", message);
                return;
            }
            var callback = channel.execCallbacks[message.id];
            if (callback) {
                delete channel.execCallbacks[message.id];
                callback(message.data);
            }
        };

        this.handlePropertyUpdate = function(message) {
            for (var i in message.signals) {
                var signal = message.signals[i];
                var object = channel.objects[signal.object];
                if (object) {
                    object.propertyUpdate(signal.signals, signal.properties);
                }
            }
        };

        this.debug = function(message) {
            channel.send({type: QWebChannelMessageTypes.Debug, data: message});
        };

        this.exec({type: QWebChannelMessageTypes.Init}, function(data) {
            for (var objectName in data) {
                var object = new QObject(objectName, data[objectName], channel);
            }
            for (var objectName in data) {
                var object = channel.objects[objectName];
                object.connectSignals();
            }
            if (initCallback) {
                initCallback(channel);
            }
            channel.send({type: QWebChannelMessageTypes.Idle});
        });
    };

    function QObject(name, data, webChannel) {
        this.__objects__ = [];
        this.__funcs__ = [];
        this.__signals__ = [];
        this.__id__ = name;
        webChannel.objects[name] = this;

        var self = this;

        this.getObject = function(objectName) {
            return webChannel.objects[objectName];
        };

        this.exec = function(methodName, args, callback) {
            var data = {
                type: QWebChannelMessageTypes.Method,
                object: self.__id__,
                method: methodName,
                args: args
            };
            webChannel.exec(data, callback);
        };

        this.signalEmitted = function(signalName, args) {
            var signal = self[signalName];
            if (signal) {
                signal.emit.apply(signal, args);
            }
        };

        this.propertyUpdate = function(signals, properties) {
            for (var name in signals) {
                var signal = self[name];
                if (signal) {
                    signal.emit.apply(signal, signals[name]);
                }
            }
            for (var name in properties) {
                self[name] = properties[name];
            }
        };

        this.connectSignals = function() {
            for (var i = 0; i < self.__signals__.length; ++i) {
                var signalName = self.__signals__[i];
                var signal = self[signalName];
                if (signal && signal.connections.length > 0) {
                    webChannel.exec({
                        type: QWebChannelMessageTypes.Signal,
                        object: self.__id__,
                        signal: signalName,
                        action: "connect"
                    });
                }
            }
        };

        for (var i = 0; i < data.methods.length; ++i) {
            var method = data.methods[i];
            this[method[0]] = (function(methodName) {
                return function() {
                    var args = [];
                    var callback;
                    for (var j = 0; j < arguments.length; ++j) {
                        if (typeof arguments[j] === "function") {
                            callback = arguments[j];
                        } else {
                            args.push(arguments[j]);
                        }
                    }
                    self.exec(methodName, args, callback);
                };
            })(method[0]);
        }

        for (var signalName in data.signals) {
            this[signalName] = {
                connections: [],
                connect: function(callback) {
                    this.connections.push(callback);
                    if (this.connections.length === 1) {
                        webChannel.exec({
                            type: QWebChannelMessageTypes.Signal,
                            object: self.__id__,
                            signal: signalName,
                            action: "connect"
                        });
                    }
                },
                disconnect: function(callback) {
                    var index = this.connections.indexOf(callback);
                    if (index !== -1) {
                        this.connections.splice(index, 1);
                        if (this.connections.length === 0) {
                            webChannel.exec({
                                type: QWebChannelMessageTypes.Signal,
                                object: self.__id__,
                                signal: signalName,
                                action: "disconnect"
                            });
                        }
                    }
                },
                emit: function() {
                    for (var j = 0; j < this.connections.length; ++j) {
                        this.connections[j].apply(null, arguments);
                    }
                }
            };
            this.__signals__.push(signalName);
        }

        for (var propertyName in data.properties) {
            this[propertyName] = data.properties[propertyName];
        }
    }

    if (typeof module !== 'undefined') {
        module.exports = {
            QWebChannel: QWebChannel
        };
    } else {
        window.QWebChannel = QWebChannel;
    }
})();
