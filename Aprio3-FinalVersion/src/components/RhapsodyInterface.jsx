import React, { useState, useEffect } from 'react';
import { CheckCircle, XCircle, Shield, Users, FileText, Settings, Play, RotateCcw, Upload, Download } from 'lucide-react';

const RhapsodyInterface = () => {
  const [rules, setRules] = useState([]);
  const [miningStatus, setMiningStatus] = useState({
    is_running: false,
    progress: 0,
    stage: '',
    message: '',
    complete: false,
    error: null
  });
  const [evaluationResult, setEvaluationResult] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadedFileName, setUploadedFileName] = useState('');
  const [availableColumns, setAvailableColumns] = useState([]);
  const [selectedColumns, setSelectedColumns] = useState([]);
  const [columnValues, setColumnValues] = useState({});
  const [columnsConfigured, setColumnsConfigured] = useState(false);
  
  // Mining parameters
  const [miningParams, setMiningParams] = useState({
    T: 20,
    K: 0.5
  });
  
  // Access request form
  const [accessRequest, setAccessRequest] = useState({
    operation: '',
    user_role: '',
    resource_type: '',
    crs_taught: ''
  });

  // API base URL - adjust if needed
  const API_BASE = '/api';

  // Poll mining status
  useEffect(() => {
    let interval;
    if (miningStatus.is_running) {
      interval = setInterval(checkMiningStatus, 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [miningStatus.is_running]);

  const checkMiningStatus = async () => {
    try {
      const response = await fetch(`${API_BASE}/status`);
      const status = await response.json();
      setMiningStatus(status);
      
      if (status.complete && !status.error) {
        await fetchRules();
      }
    } catch (error) {
      console.error('Error checking status:', error);
    }
  };

  const fetchRules = async () => {
    try {
      const response = await fetch(`${API_BASE}/rules`);
      const data = await response.json();
      if (response.ok) {
        setRules(data.rules || []);
      }
    } catch (error) {
      console.error('Error fetching rules:', error);
    }
  };

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    setSelectedFile(file);
  };

  const uploadFile = async () => {
    if (!selectedFile) {
      alert('Please select a CSV file first');
      return;
    }

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await fetch(`${API_BASE}/upload`, {
        method: 'POST',
        body: formData
      });
      
      const result = await response.json();
      
      if (response.ok) {
        setUploadedFileName(result.filename);
        setAvailableColumns(result.columns || []);       
        setColumnValues(result.column_values || {});    
        setSelectedColumns([]);                          
        setColumnsConfigured(false);                     
        setAccessRequest({});                      
        alert(`File uploaded successfully! ${result.rows} rows found.`);
      } else {
        alert(`Upload error: ${result.error}`);
      }
    } catch (error) {
      console.error('Upload error:', error);
      alert('Upload failed. Please try again.');
    }
  };

  const startMining = async () => {
    if (!uploadedFileName) {
      alert('Please upload a CSV file first');
      return;
    }
    if (!columnsConfigured || selectedColumns.length === 0) {  // NEW validation
      alert('Please configure columns first');
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/mine`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          filename: uploadedFileName,
          T: miningParams.T,
          K: miningParams.K,
          selected_columns: selectedColumns  
        })
      });
      
      const result = await response.json();
      
      if (response.ok) {
        setMiningStatus(prev => ({ ...prev, is_running: true }));
      } else {
        alert(`Mining error: ${result.error}`);
      }
    } catch (error) {
      console.error('Mining error:', error);
      alert('Failed to start mining. Please try again.');
    }
  };

  const evaluateAccess = async () => {
    try {
      const response = await fetch(`${API_BASE}/evaluate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(accessRequest)
      });
      
      const result = await response.json();
      
      if (response.ok) {
        setEvaluationResult(result);
      } else {
        alert(`Evaluation error: ${result.error}`);
      }
    } catch (error) {
      console.error('Evaluation error:', error);
      alert('Failed to evaluate request. Please try again.');
    }
  };

  const resetSystem = async () => {
    try {
      const response = await fetch(`${API_BASE}/reset`, {
        method: 'POST'
      });
      
      if (response.ok) {
        setRules([]);
        setMiningStatus({
          is_running: false,
          progress: 0,
          stage: '',
          message: '',
          complete: false,
          error: null
        });
        setEvaluationResult(null);
        setUploadedFileName('');
        setSelectedFile(null);
        alert('System reset successfully');
      }
    } catch (error) {
      console.error('Reset error:', error);
      alert('Failed to reset system');
    }
  };

  const resetForm = () => {
    setAccessRequest({
      operation: '',
      user_role: '',
      resource_type: '',
      crs_taught: ''
    });
    setEvaluationResult(null);
  };

  const handleInputChange = (field, value) => {
    setAccessRequest(prev => ({
      ...prev,
      [field]: value
    }));
    if (evaluationResult) {
      setEvaluationResult(null);
    }
  };

  const handleColumnToggle = (column) => {
  setSelectedColumns(prev => {
    if (prev.includes(column)) {
      return prev.filter(col => col !== column);
    } else {
      return [...prev, column];
    }
    });
  };

const confirmColumnSelection = () => {
  if (selectedColumns.length === 0) {
    alert('Please select at least one column');
    return;
  }
  setColumnsConfigured(true);
  // Reset access request form to match selected columns
  const newAccessRequest = {};
  selectedColumns.forEach(col => {
    newAccessRequest[col] = '';
    });
  setAccessRequest(newAccessRequest);
  };

  return (
    <div className="max-w-7xl mx-auto p-6 bg-gray-50 min-h-screen">
      <div className="bg-white rounded-lg shadow-lg p-8">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center">
            <Shield className="w-8 h-8 text-blue-600 mr-3" />
            <h1 className="text-3xl font-bold text-gray-800">RHAPSODY Policy Mining & Evaluation</h1>
          </div>
          <button
            onClick={resetSystem}
            className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 flex items-center"
          >
            <RotateCcw className="w-4 h-4 mr-2" />
            Reset System
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left Panel: File Upload & Mining Control */}
          <div className="space-y-6">
            {/* File Upload Section */}
            <div className="bg-purple-50 p-6 rounded-lg">
              <h2 className="text-xl font-semibold text-purple-800 mb-4 flex items-center">
                <Upload className="w-5 h-5 mr-2" />
                Data Upload
              </h2>
              
              <div className="space-y-4">
                <div>
                  <input
                    type="file"
                    accept=".csv"
                    onChange={handleFileSelect}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                  />
                </div>
                
                <button
                  onClick={uploadFile}
                  disabled={!selectedFile}
                  className="w-full bg-purple-600 text-white py-2 px-4 rounded-md hover:bg-purple-700 disabled:bg-purple-300 flex items-center justify-center"
                >
                  <Upload className="w-4 h-4 mr-2" />
                  Upload CSV File
                </button>
                
                {uploadedFileName && (
                  <div className="bg-white p-3 rounded border">
                    <p className="text-sm text-green-600">
                      ✓ Uploaded: {uploadedFileName}
                    </p>
                  </div>
                )}
              </div>
            </div>
            {/* Column Selection Section */}
            {availableColumns.length > 0 && !columnsConfigured && (
              <div className="bg-orange-50 p-6 rounded-lg">
                <h2 className="text-xl font-semibold text-orange-800 mb-4 flex items-center">
                  <Settings className="w-5 h-5 mr-2" />
                  Select Columns for Mining
                </h2>
                
                <div className="space-y-4">
                  <p className="text-sm text-gray-600">
                    Choose which columns to include in the policy mining process:
                  </p>
                  
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    {availableColumns.map((column) => (
                      <label key={column} className="flex items-center space-x-2 p-2 border rounded hover:bg-orange-100">
                        <input
                          type="checkbox"
                          checked={selectedColumns.includes(column)}
                          onChange={() => handleColumnToggle(column)}
                          className="form-checkbox h-4 w-4 text-orange-600"
                        />
                        <span className="text-sm font-medium">{column}</span>
                        <span className="text-xs text-gray-500">
                          ({(columnValues[column] || []).length} values)
                        </span>
                      </label>
                    ))}
                  </div>
                  
                  <button
                    onClick={confirmColumnSelection}
                    disabled={selectedColumns.length === 0}
                    className="w-full bg-orange-600 text-white py-2 px-4 rounded-md hover:bg-orange-700 disabled:bg-orange-300"
                  >
                    Confirm Column Selection ({selectedColumns.length} selected)
                  </button>
                </div>
              </div>
            )}

            {/* Mining Parameters Section */}
            <div className="bg-blue-50 p-6 rounded-lg">
              <h2 className="text-xl font-semibold text-blue-800 mb-4 flex items-center">
                <Settings className="w-5 h-5 mr-2" />
                RHAPSODY Mining Parameters
              </h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">T (Support Threshold)</label>
                  <input
                    type="number"
                    value={miningParams.T}
                    onChange={(e) => setMiningParams(prev => ({...prev, T: parseInt(e.target.value) || 20}))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    min="1"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">K (Reliability Threshold)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={miningParams.K}
                    onChange={(e) => setMiningParams(prev => ({...prev, K: parseFloat(e.target.value) || 0.5}))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    min="0"
                    max="1"
                  />
                </div>
              </div>

              <button
                onClick={startMining}
                disabled={miningStatus.is_running || !uploadedFileName}
                className="w-full bg-blue-600 text-white py-3 px-4 rounded-md hover:bg-blue-700 disabled:bg-blue-300 flex items-center justify-center"
              >
                {miningStatus.is_running ? (
                  <>
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                    Mining Policies...
                  </>
                ) : (
                  <>
                    <Play className="w-5 h-5 mr-2" />
                    Run RHAPSODY Mining
                  </>
                )}
              </button>

              {/* Mining Progress */}
              {miningStatus.is_running && (
                <div className="mt-4">
                  <div className="flex justify-between text-sm text-gray-600 mb-1">
                    <span>{miningStatus.stage}</span>
                    <span>{miningStatus.progress}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${miningStatus.progress}%` }}
                    ></div>
                  </div>
                  <p className="text-sm text-gray-600 mt-2">{miningStatus.message}</p>
                </div>
              )}

              {/* Error Display */}
              {miningStatus.error && (
                <div className="mt-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
                  Error: {miningStatus.error}
                </div>
              )}
            </div>

            {/* Mined Rules Display */}
            <div className="bg-gray-50 p-6 rounded-lg">
              <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
                <FileText className="w-5 h-5 mr-2" />
                Mined Policy Rules ({rules.length})
              </h3>
              
              {rules.length === 0 ? (
                <p className="text-gray-500 italic">No rules mined yet. Upload data and run the algorithm first.</p>
              ) : (
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {rules.map((rule, index) => (
                    <div key={index} className="bg-white p-3 rounded border text-sm font-mono">
                      {rule}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Right Panel: Access Evaluation */}
          <div className="space-y-6">
            <div className="bg-green-50 p-6 rounded-lg">
              <h2 className="text-xl font-semibold text-green-800 mb-4 flex items-center">
                <Users className="w-5 h-5 mr-2" />
                Access Request Evaluation
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                {selectedColumns.map((column) => (
                  <div key={column}>
                    <label className="block text-sm font-medium text-gray-700 mb-1 capitalize">
                      {column.replace('_', ' ')}
                    </label>
                    <select
                      value={accessRequest[column] || ''}
                      onChange={(e) => handleInputChange(column, e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                    >
                      <option value="">Select {column}</option>
                      {(columnValues[column] || []).map(value => (
                        <option key={value} value={value}>{value}</option>
                      ))}
                    </select>
                  </div>
                ))}
              </div>

              <div className="flex space-x-3">
                <button
                  onClick={evaluateAccess}
                  disabled={!miningStatus.complete}
                  className="flex-1 bg-green-600 text-white py-3 px-4 rounded-md hover:bg-green-700 disabled:bg-gray-400 flex items-center justify-center"
                >
                  <Play className="w-5 h-5 mr-2" />
                  Evaluate Request
                </button>
                
                <button
                  onClick={resetForm}
                  className="bg-gray-500 text-white py-3 px-4 rounded-md hover:bg-gray-600 flex items-center"
                >
                  <RotateCcw className="w-4 h-4 mr-2" />
                  Reset Form
                </button>
              </div>

              {/* Evaluation Result */}
              {evaluationResult && (
                <div className="mt-6 p-4 rounded-lg border">
                  <h3 className="font-semibold mb-3 flex items-center">
                    {evaluationResult.granted ? (
                      <CheckCircle className="w-5 h-5 text-green-600 mr-2" />
                    ) : (
                      <XCircle className="w-5 h-5 text-red-600 mr-2" />
                    )}
                    Access Decision: {evaluationResult.granted ? 'GRANTED' : 'DENIED'}
                  </h3>
                  
                  <div className="bg-gray-50 p-3 rounded mt-2">
                    <p className="text-sm text-gray-700">
                      <strong>Message:</strong> {evaluationResult.message}
                    </p>
                  </div>
                  
                  {evaluationResult.matching_rule && (
                    <div className="bg-blue-50 p-3 rounded mt-2">
                      <p className="text-sm text-blue-800">
                        <strong>Matched Rule:</strong>
                      </p>
                      <code className="text-xs bg-white p-2 rounded block mt-1">
                        {evaluationResult.matching_rule}
                      </code>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* System Status */}
            <div className="bg-yellow-50 p-6 rounded-lg">
              <h3 className="text-lg font-semibold text-yellow-800 mb-4 flex items-center">
                <Settings className="w-5 h-5 mr-2" />
                System Status
              </h3>
              
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span>Data Uploaded:</span>
                  <span className={uploadedFileName ? 'text-green-600' : 'text-red-600'}>
                    {uploadedFileName ? '✓ Yes' : '✗ No'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Columns Configured:</span>
                  <span className={columnsConfigured ? 'text-green-600' : 'text-red-600'}>
                    {columnsConfigured ? `✓ ${selectedColumns.length} columns` : '✗ Not configured'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Mining Complete:</span>
                  <span className={miningStatus.complete ? 'text-green-600' : 'text-red-600'}>
                    {miningStatus.complete ? '✓ Yes' : '✗ No'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Rules Available:</span>
                  <span className={rules.length > 0 ? 'text-green-600' : 'text-red-600'}>
                    {rules.length > 0 ? `✓ ${rules.length} rules` : '✗ None'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Evaluation Ready:</span>
                  <span className={miningStatus.complete ? 'text-green-600' : 'text-red-600'}>
                    {miningStatus.complete ? '✓ Ready' : '✗ Not Ready'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RhapsodyInterface;