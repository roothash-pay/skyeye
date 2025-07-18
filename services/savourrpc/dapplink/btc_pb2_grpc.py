# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc
import warnings

from dapplink import btc_pb2 as dapplink_dot_btc__pb2

GRPC_GENERATED_VERSION = '1.70.0'
GRPC_VERSION = grpc.__version__
_version_not_supported = False

try:
    from grpc._utilities import first_version_is_lower
    _version_not_supported = first_version_is_lower(GRPC_VERSION, GRPC_GENERATED_VERSION)
except ImportError:
    _version_not_supported = True

if _version_not_supported:
    raise RuntimeError(
        f'The grpc package installed is at version {GRPC_VERSION},'
        + f' but the generated code in dapplink/btc_pb2_grpc.py depends on'
        + f' grpcio>={GRPC_GENERATED_VERSION}.'
        + f' Please upgrade your grpc module to grpcio>={GRPC_GENERATED_VERSION}'
        + f' or downgrade your generated code using grpcio-tools<={GRPC_VERSION}.'
    )


class WalletBtcServiceStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.getSupportChains = channel.unary_unary(
                '/dapplink.btc.WalletBtcService/getSupportChains',
                request_serializer=dapplink_dot_btc__pb2.SupportChainsRequest.SerializeToString,
                response_deserializer=dapplink_dot_btc__pb2.SupportChainsResponse.FromString,
                _registered_method=True)
        self.convertAddress = channel.unary_unary(
                '/dapplink.btc.WalletBtcService/convertAddress',
                request_serializer=dapplink_dot_btc__pb2.ConvertAddressRequest.SerializeToString,
                response_deserializer=dapplink_dot_btc__pb2.ConvertAddressResponse.FromString,
                _registered_method=True)
        self.validAddress = channel.unary_unary(
                '/dapplink.btc.WalletBtcService/validAddress',
                request_serializer=dapplink_dot_btc__pb2.ValidAddressRequest.SerializeToString,
                response_deserializer=dapplink_dot_btc__pb2.ValidAddressResponse.FromString,
                _registered_method=True)
        self.getFee = channel.unary_unary(
                '/dapplink.btc.WalletBtcService/getFee',
                request_serializer=dapplink_dot_btc__pb2.FeeRequest.SerializeToString,
                response_deserializer=dapplink_dot_btc__pb2.FeeResponse.FromString,
                _registered_method=True)
        self.getAccount = channel.unary_unary(
                '/dapplink.btc.WalletBtcService/getAccount',
                request_serializer=dapplink_dot_btc__pb2.AccountRequest.SerializeToString,
                response_deserializer=dapplink_dot_btc__pb2.AccountResponse.FromString,
                _registered_method=True)
        self.getUnspentOutputs = channel.unary_unary(
                '/dapplink.btc.WalletBtcService/getUnspentOutputs',
                request_serializer=dapplink_dot_btc__pb2.UnspentOutputsRequest.SerializeToString,
                response_deserializer=dapplink_dot_btc__pb2.UnspentOutputsResponse.FromString,
                _registered_method=True)
        self.getBlockByNumber = channel.unary_unary(
                '/dapplink.btc.WalletBtcService/getBlockByNumber',
                request_serializer=dapplink_dot_btc__pb2.BlockNumberRequest.SerializeToString,
                response_deserializer=dapplink_dot_btc__pb2.BlockResponse.FromString,
                _registered_method=True)
        self.getBlockByHash = channel.unary_unary(
                '/dapplink.btc.WalletBtcService/getBlockByHash',
                request_serializer=dapplink_dot_btc__pb2.BlockHashRequest.SerializeToString,
                response_deserializer=dapplink_dot_btc__pb2.BlockResponse.FromString,
                _registered_method=True)
        self.getBlockHeaderByHash = channel.unary_unary(
                '/dapplink.btc.WalletBtcService/getBlockHeaderByHash',
                request_serializer=dapplink_dot_btc__pb2.BlockHeaderHashRequest.SerializeToString,
                response_deserializer=dapplink_dot_btc__pb2.BlockHeaderResponse.FromString,
                _registered_method=True)
        self.getBlockHeaderByNumber = channel.unary_unary(
                '/dapplink.btc.WalletBtcService/getBlockHeaderByNumber',
                request_serializer=dapplink_dot_btc__pb2.BlockHeaderNumberRequest.SerializeToString,
                response_deserializer=dapplink_dot_btc__pb2.BlockHeaderResponse.FromString,
                _registered_method=True)
        self.SendTx = channel.unary_unary(
                '/dapplink.btc.WalletBtcService/SendTx',
                request_serializer=dapplink_dot_btc__pb2.SendTxRequest.SerializeToString,
                response_deserializer=dapplink_dot_btc__pb2.SendTxResponse.FromString,
                _registered_method=True)
        self.getTxByAddress = channel.unary_unary(
                '/dapplink.btc.WalletBtcService/getTxByAddress',
                request_serializer=dapplink_dot_btc__pb2.TxAddressRequest.SerializeToString,
                response_deserializer=dapplink_dot_btc__pb2.TxAddressResponse.FromString,
                _registered_method=True)
        self.getTxByHash = channel.unary_unary(
                '/dapplink.btc.WalletBtcService/getTxByHash',
                request_serializer=dapplink_dot_btc__pb2.TxHashRequest.SerializeToString,
                response_deserializer=dapplink_dot_btc__pb2.TxHashResponse.FromString,
                _registered_method=True)
        self.createUnSignTransaction = channel.unary_unary(
                '/dapplink.btc.WalletBtcService/createUnSignTransaction',
                request_serializer=dapplink_dot_btc__pb2.UnSignTransactionRequest.SerializeToString,
                response_deserializer=dapplink_dot_btc__pb2.UnSignTransactionResponse.FromString,
                _registered_method=True)
        self.buildSignedTransaction = channel.unary_unary(
                '/dapplink.btc.WalletBtcService/buildSignedTransaction',
                request_serializer=dapplink_dot_btc__pb2.SignedTransactionRequest.SerializeToString,
                response_deserializer=dapplink_dot_btc__pb2.SignedTransactionResponse.FromString,
                _registered_method=True)
        self.decodeTransaction = channel.unary_unary(
                '/dapplink.btc.WalletBtcService/decodeTransaction',
                request_serializer=dapplink_dot_btc__pb2.DecodeTransactionRequest.SerializeToString,
                response_deserializer=dapplink_dot_btc__pb2.DecodeTransactionResponse.FromString,
                _registered_method=True)
        self.verifySignedTransaction = channel.unary_unary(
                '/dapplink.btc.WalletBtcService/verifySignedTransaction',
                request_serializer=dapplink_dot_btc__pb2.VerifyTransactionRequest.SerializeToString,
                response_deserializer=dapplink_dot_btc__pb2.VerifyTransactionResponse.FromString,
                _registered_method=True)


class WalletBtcServiceServicer(object):
    """Missing associated documentation comment in .proto file."""

    def getSupportChains(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def convertAddress(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def validAddress(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def getFee(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def getAccount(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def getUnspentOutputs(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def getBlockByNumber(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def getBlockByHash(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def getBlockHeaderByHash(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def getBlockHeaderByNumber(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def SendTx(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def getTxByAddress(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def getTxByHash(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def createUnSignTransaction(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def buildSignedTransaction(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def decodeTransaction(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def verifySignedTransaction(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_WalletBtcServiceServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'getSupportChains': grpc.unary_unary_rpc_method_handler(
                    servicer.getSupportChains,
                    request_deserializer=dapplink_dot_btc__pb2.SupportChainsRequest.FromString,
                    response_serializer=dapplink_dot_btc__pb2.SupportChainsResponse.SerializeToString,
            ),
            'convertAddress': grpc.unary_unary_rpc_method_handler(
                    servicer.convertAddress,
                    request_deserializer=dapplink_dot_btc__pb2.ConvertAddressRequest.FromString,
                    response_serializer=dapplink_dot_btc__pb2.ConvertAddressResponse.SerializeToString,
            ),
            'validAddress': grpc.unary_unary_rpc_method_handler(
                    servicer.validAddress,
                    request_deserializer=dapplink_dot_btc__pb2.ValidAddressRequest.FromString,
                    response_serializer=dapplink_dot_btc__pb2.ValidAddressResponse.SerializeToString,
            ),
            'getFee': grpc.unary_unary_rpc_method_handler(
                    servicer.getFee,
                    request_deserializer=dapplink_dot_btc__pb2.FeeRequest.FromString,
                    response_serializer=dapplink_dot_btc__pb2.FeeResponse.SerializeToString,
            ),
            'getAccount': grpc.unary_unary_rpc_method_handler(
                    servicer.getAccount,
                    request_deserializer=dapplink_dot_btc__pb2.AccountRequest.FromString,
                    response_serializer=dapplink_dot_btc__pb2.AccountResponse.SerializeToString,
            ),
            'getUnspentOutputs': grpc.unary_unary_rpc_method_handler(
                    servicer.getUnspentOutputs,
                    request_deserializer=dapplink_dot_btc__pb2.UnspentOutputsRequest.FromString,
                    response_serializer=dapplink_dot_btc__pb2.UnspentOutputsResponse.SerializeToString,
            ),
            'getBlockByNumber': grpc.unary_unary_rpc_method_handler(
                    servicer.getBlockByNumber,
                    request_deserializer=dapplink_dot_btc__pb2.BlockNumberRequest.FromString,
                    response_serializer=dapplink_dot_btc__pb2.BlockResponse.SerializeToString,
            ),
            'getBlockByHash': grpc.unary_unary_rpc_method_handler(
                    servicer.getBlockByHash,
                    request_deserializer=dapplink_dot_btc__pb2.BlockHashRequest.FromString,
                    response_serializer=dapplink_dot_btc__pb2.BlockResponse.SerializeToString,
            ),
            'getBlockHeaderByHash': grpc.unary_unary_rpc_method_handler(
                    servicer.getBlockHeaderByHash,
                    request_deserializer=dapplink_dot_btc__pb2.BlockHeaderHashRequest.FromString,
                    response_serializer=dapplink_dot_btc__pb2.BlockHeaderResponse.SerializeToString,
            ),
            'getBlockHeaderByNumber': grpc.unary_unary_rpc_method_handler(
                    servicer.getBlockHeaderByNumber,
                    request_deserializer=dapplink_dot_btc__pb2.BlockHeaderNumberRequest.FromString,
                    response_serializer=dapplink_dot_btc__pb2.BlockHeaderResponse.SerializeToString,
            ),
            'SendTx': grpc.unary_unary_rpc_method_handler(
                    servicer.SendTx,
                    request_deserializer=dapplink_dot_btc__pb2.SendTxRequest.FromString,
                    response_serializer=dapplink_dot_btc__pb2.SendTxResponse.SerializeToString,
            ),
            'getTxByAddress': grpc.unary_unary_rpc_method_handler(
                    servicer.getTxByAddress,
                    request_deserializer=dapplink_dot_btc__pb2.TxAddressRequest.FromString,
                    response_serializer=dapplink_dot_btc__pb2.TxAddressResponse.SerializeToString,
            ),
            'getTxByHash': grpc.unary_unary_rpc_method_handler(
                    servicer.getTxByHash,
                    request_deserializer=dapplink_dot_btc__pb2.TxHashRequest.FromString,
                    response_serializer=dapplink_dot_btc__pb2.TxHashResponse.SerializeToString,
            ),
            'createUnSignTransaction': grpc.unary_unary_rpc_method_handler(
                    servicer.createUnSignTransaction,
                    request_deserializer=dapplink_dot_btc__pb2.UnSignTransactionRequest.FromString,
                    response_serializer=dapplink_dot_btc__pb2.UnSignTransactionResponse.SerializeToString,
            ),
            'buildSignedTransaction': grpc.unary_unary_rpc_method_handler(
                    servicer.buildSignedTransaction,
                    request_deserializer=dapplink_dot_btc__pb2.SignedTransactionRequest.FromString,
                    response_serializer=dapplink_dot_btc__pb2.SignedTransactionResponse.SerializeToString,
            ),
            'decodeTransaction': grpc.unary_unary_rpc_method_handler(
                    servicer.decodeTransaction,
                    request_deserializer=dapplink_dot_btc__pb2.DecodeTransactionRequest.FromString,
                    response_serializer=dapplink_dot_btc__pb2.DecodeTransactionResponse.SerializeToString,
            ),
            'verifySignedTransaction': grpc.unary_unary_rpc_method_handler(
                    servicer.verifySignedTransaction,
                    request_deserializer=dapplink_dot_btc__pb2.VerifyTransactionRequest.FromString,
                    response_serializer=dapplink_dot_btc__pb2.VerifyTransactionResponse.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'dapplink.btc.WalletBtcService', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))
    server.add_registered_method_handlers('dapplink.btc.WalletBtcService', rpc_method_handlers)


 # This class is part of an EXPERIMENTAL API.
class WalletBtcService(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def getSupportChains(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/dapplink.btc.WalletBtcService/getSupportChains',
            dapplink_dot_btc__pb2.SupportChainsRequest.SerializeToString,
            dapplink_dot_btc__pb2.SupportChainsResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def convertAddress(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/dapplink.btc.WalletBtcService/convertAddress',
            dapplink_dot_btc__pb2.ConvertAddressRequest.SerializeToString,
            dapplink_dot_btc__pb2.ConvertAddressResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def validAddress(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/dapplink.btc.WalletBtcService/validAddress',
            dapplink_dot_btc__pb2.ValidAddressRequest.SerializeToString,
            dapplink_dot_btc__pb2.ValidAddressResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def getFee(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/dapplink.btc.WalletBtcService/getFee',
            dapplink_dot_btc__pb2.FeeRequest.SerializeToString,
            dapplink_dot_btc__pb2.FeeResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def getAccount(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/dapplink.btc.WalletBtcService/getAccount',
            dapplink_dot_btc__pb2.AccountRequest.SerializeToString,
            dapplink_dot_btc__pb2.AccountResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def getUnspentOutputs(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/dapplink.btc.WalletBtcService/getUnspentOutputs',
            dapplink_dot_btc__pb2.UnspentOutputsRequest.SerializeToString,
            dapplink_dot_btc__pb2.UnspentOutputsResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def getBlockByNumber(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/dapplink.btc.WalletBtcService/getBlockByNumber',
            dapplink_dot_btc__pb2.BlockNumberRequest.SerializeToString,
            dapplink_dot_btc__pb2.BlockResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def getBlockByHash(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/dapplink.btc.WalletBtcService/getBlockByHash',
            dapplink_dot_btc__pb2.BlockHashRequest.SerializeToString,
            dapplink_dot_btc__pb2.BlockResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def getBlockHeaderByHash(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/dapplink.btc.WalletBtcService/getBlockHeaderByHash',
            dapplink_dot_btc__pb2.BlockHeaderHashRequest.SerializeToString,
            dapplink_dot_btc__pb2.BlockHeaderResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def getBlockHeaderByNumber(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/dapplink.btc.WalletBtcService/getBlockHeaderByNumber',
            dapplink_dot_btc__pb2.BlockHeaderNumberRequest.SerializeToString,
            dapplink_dot_btc__pb2.BlockHeaderResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def SendTx(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/dapplink.btc.WalletBtcService/SendTx',
            dapplink_dot_btc__pb2.SendTxRequest.SerializeToString,
            dapplink_dot_btc__pb2.SendTxResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def getTxByAddress(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/dapplink.btc.WalletBtcService/getTxByAddress',
            dapplink_dot_btc__pb2.TxAddressRequest.SerializeToString,
            dapplink_dot_btc__pb2.TxAddressResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def getTxByHash(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/dapplink.btc.WalletBtcService/getTxByHash',
            dapplink_dot_btc__pb2.TxHashRequest.SerializeToString,
            dapplink_dot_btc__pb2.TxHashResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def createUnSignTransaction(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/dapplink.btc.WalletBtcService/createUnSignTransaction',
            dapplink_dot_btc__pb2.UnSignTransactionRequest.SerializeToString,
            dapplink_dot_btc__pb2.UnSignTransactionResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def buildSignedTransaction(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/dapplink.btc.WalletBtcService/buildSignedTransaction',
            dapplink_dot_btc__pb2.SignedTransactionRequest.SerializeToString,
            dapplink_dot_btc__pb2.SignedTransactionResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def decodeTransaction(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/dapplink.btc.WalletBtcService/decodeTransaction',
            dapplink_dot_btc__pb2.DecodeTransactionRequest.SerializeToString,
            dapplink_dot_btc__pb2.DecodeTransactionResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def verifySignedTransaction(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/dapplink.btc.WalletBtcService/verifySignedTransaction',
            dapplink_dot_btc__pb2.VerifyTransactionRequest.SerializeToString,
            dapplink_dot_btc__pb2.VerifyTransactionResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)
