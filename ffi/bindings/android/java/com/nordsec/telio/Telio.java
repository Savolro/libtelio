/* ----------------------------------------------------------------------------
 * This file was automatically generated by SWIG (http://www.swig.org).
 * Version 4.0.2
 *
 * Do not make changes to this file unless you know what you are doing--modify
 * the SWIG interface file instead.
 * ----------------------------------------------------------------------------- */

package com.nordsec.telio;

public class Telio {
  private transient long swigCPtr;
  protected transient boolean swigCMemOwn;

  protected Telio(long cPtr, boolean cMemoryOwn) {
    swigCMemOwn = cMemoryOwn;
    swigCPtr = cPtr;
  }

  protected static long getCPtr(Telio obj) {
    return (obj == null) ? 0 : obj.swigCPtr;
  }

  @SuppressWarnings("deprecation")
  protected void finalize() {
    delete();
  }

  public synchronized void delete() {
    if (swigCPtr != 0) {
      if (swigCMemOwn) {
        swigCMemOwn = false;
        libtelioJNI.delete_Telio(swigCPtr);
      }
      swigCPtr = 0;
    }
  }

  public Telio(String features, ITelioEventCb events, TelioLogLevel level, ITelioLoggerCb logger, ITelioProtectCb protect, java.lang.Object ctx) {
    this(libtelioJNI.new_Telio(features, events, level.swigValue(), logger, protect, ctx), true);
  }

  public static TelioAdapterType getDefaultAdapter() {
    return TelioAdapterType.swigToEnum(libtelioJNI.Telio_getDefaultAdapter());
  }

  public TelioResult start(String privateKey, TelioAdapterType adapter) {
    return TelioResult.swigToEnum(libtelioJNI.Telio_start(swigCPtr, this, privateKey, adapter.swigValue()));
  }

  public TelioResult startNamed(String privateKey, TelioAdapterType adapter, String name) {
    return TelioResult.swigToEnum(libtelioJNI.Telio_startNamed(swigCPtr, this, privateKey, adapter.swigValue(), name));
  }

  public TelioResult startWithTun(String privateKey, TelioAdapterType adapter, int tun) {
    return TelioResult.swigToEnum(libtelioJNI.Telio_startWithTun(swigCPtr, this, privateKey, adapter.swigValue(), tun));
  }

  public TelioResult enableMagicDns(String forwardServers) {
    return TelioResult.swigToEnum(libtelioJNI.Telio_enableMagicDns(swigCPtr, this, forwardServers));
  }

  public TelioResult disableMagicDns() {
    return TelioResult.swigToEnum(libtelioJNI.Telio_disableMagicDns(swigCPtr, this));
  }

  public TelioResult stop() {
    return TelioResult.swigToEnum(libtelioJNI.Telio_stop(swigCPtr, this));
  }

  public java.math.BigInteger getAdapterLuid() {
    return libtelioJNI.Telio_getAdapterLuid(swigCPtr, this);
  }

  public TelioResult setPrivateKey(String privateKey) {
    return TelioResult.swigToEnum(libtelioJNI.Telio_setPrivateKey(swigCPtr, this, privateKey));
  }

  public String getPrivateKey() {
    return libtelioJNI.Telio_getPrivateKey(swigCPtr, this);
  }

  public TelioResult notifyNetworkChange(String notifyInfo) {
    return TelioResult.swigToEnum(libtelioJNI.Telio_notifyNetworkChange(swigCPtr, this, notifyInfo));
  }

  public TelioResult connectToExitNode(String publicKey, String allowedIps, String endpoint) {
    return TelioResult.swigToEnum(libtelioJNI.Telio_connectToExitNode(swigCPtr, this, publicKey, allowedIps, endpoint));
  }

  public TelioResult connectToExitNodeWithId(String identifier, String publicKey, String allowedIps, String endpoint) {
    return TelioResult.swigToEnum(libtelioJNI.Telio_connectToExitNodeWithId(swigCPtr, this, identifier, publicKey, allowedIps, endpoint));
  }

  public TelioResult disconnectFromExitNode(String publicKey) {
    return TelioResult.swigToEnum(libtelioJNI.Telio_disconnectFromExitNode(swigCPtr, this, publicKey));
  }

  public TelioResult disconnectFromExitNodes() {
    return TelioResult.swigToEnum(libtelioJNI.Telio_disconnectFromExitNodes(swigCPtr, this));
  }

  public TelioResult setMeshnet(String cfg) {
    return TelioResult.swigToEnum(libtelioJNI.Telio_setMeshnet(swigCPtr, this, cfg));
  }

  public TelioResult setMeshnetOff() {
    return TelioResult.swigToEnum(libtelioJNI.Telio_setMeshnetOff(swigCPtr, this));
  }

  public String generateSecretKey() {
    return libtelioJNI.Telio_generateSecretKey(swigCPtr, this);
  }

  public String generatePublicKey(String secretKey) {
    return libtelioJNI.Telio_generatePublicKey(swigCPtr, this, secretKey);
  }

  public String getStatusMap() {
    return libtelioJNI.Telio_getStatusMap(swigCPtr, this);
  }

  public String getLastError() {
    return libtelioJNI.Telio_getLastError(swigCPtr, this);
  }

  public static String getVersionTag() {
    return libtelioJNI.Telio_getVersionTag();
  }

  public static String getCommitSha() {
    return libtelioJNI.Telio_getCommitSha();
  }

}
