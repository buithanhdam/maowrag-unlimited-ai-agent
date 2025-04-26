'use client';
import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '@/components/ui/alert-dialog';
import { Textarea } from '@/components/ui/textarea';

interface Foundation {
  id: number;
  provider: string;
  model_id: string;
  description?: string;
  capabilities?: any;
  is_active?: boolean;
}

interface Config {
  id: number;
  foundation_id: number;
  name: string;
  temperature: number;
  max_tokens: number;
  top_p?: number;
  frequency_penalty?: number;
  presence_penalty?: number;
  system_prompt: string;
  stop_sequences?: string[];
}

const defaultFoundation: Foundation = {
  id: 0,
  provider: '',
  model_id: '',
  description: '',
  capabilities: {}
}

const defaultConfig: Config = {
  id: 0,
  foundation_id: 0,
  name: '',
  temperature: 0.7,
  max_tokens: 100,
  top_p: 1,
  frequency_penalty: 0,
  presence_penalty: 0,
  system_prompt: '',
  stop_sequences: []
}
const ProviderTypeMap: Record<string, string> = {
  OPENAI :"openai",
  GOOGLE: "google",
  ANTHROPIC :"anthropic"
};
const BACKEND_API_URL = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000';

const LLMComponent = () => {
  const [foundations, setFoundations] = useState<Foundation[]>([]);
  const [selectedFoundation, setSelectedFoundation] = useState<Foundation | null>(null);
  const [configs, setConfigs] = useState<Config[]>([]);
  const [showFoundationForm, setShowFoundationForm] = useState(false);
  const [showConfigForm, setShowConfigForm] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [foundationFormTitle, setFoundationFormTitle] = useState("Add LLM Foundation");
  const [configFormTitle, setConfigFormTitle] = useState("Add LLM Config");

  // Foundation form state
  const [foundationForm, setFoundationForm] = useState<Foundation>(defaultFoundation);

  // Config form state
  const [configForm, setConfigForm] = useState<Config>(defaultConfig);

  // Reset forms when dialogs close
  useEffect(() => {
    if (!showFoundationForm && !isEditing) {
      setFoundationForm(defaultFoundation);
      setFoundationFormTitle("Add LLM Foundation");
    }
  }, [showFoundationForm]);

  useEffect(() => {
    if (!showConfigForm && !isEditing) {
      setConfigForm({...defaultConfig, foundation_id: selectedFoundation?.id || 0});
      setConfigFormTitle("Add LLM Config");
    }
  }, [showConfigForm, selectedFoundation]);

  // Fetch foundations
  const fetchFoundations = async () => {
    try {
      const response = await fetch(`${BACKEND_API_URL}/llm/foundations/get`);
      const data = await response.json();
      setFoundations(data);
    } catch (error) {
      console.error('Error fetching foundations:', error);
    }
  };

  // Fetch configs for a foundation
  const fetchConfigs = async (foundationId: number) => {
    if (!foundationId) return;
    try {
      const response = await fetch(`${BACKEND_API_URL}/llm/foundations/${foundationId}/configs`);
      const data = await response.json();
      setConfigs(data);
    } catch (error) {
      console.error('Error fetching configs:', error);
    }
  };

  // Create or update foundation
  const handleFoundationSubmit = async () => {
    try {
      let response;
      if (isEditing) {
        // Update existing foundation
        response = await fetch(`${BACKEND_API_URL}/llm/foundations/update/${foundationForm.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            provider: foundationForm.provider,
            model_id: foundationForm.model_id,
            description: foundationForm.description,
            capabilities: foundationForm.capabilities,
            is_active: foundationForm.is_active
          })
        });
      } else {
        // Create new foundation
        response = await fetch(`${BACKEND_API_URL}/llm/foundations/create`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(foundationForm)
        });
      }
      
      if (response.ok) {
        setShowFoundationForm(false);
        setFoundationForm(defaultFoundation);
        setIsEditing(false);
        fetchFoundations();
      }
    } catch (error) {
      console.error('Error submitting foundation:', error);
    }
  };

  // Create or update config
  const handleConfigSubmit = async () => {
    try {
      let response;
      if (isEditing) {
        // Update existing config
        response = await fetch(`${BACKEND_API_URL}/llm/configs/update/${configForm.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: configForm.name,
            temperature: configForm.temperature,
            max_tokens: configForm.max_tokens,
            top_p: configForm.top_p,
            frequency_penalty: configForm.frequency_penalty,
            presence_penalty: configForm.presence_penalty,
            system_prompt: configForm.system_prompt,
            stop_sequences: configForm.stop_sequences
          })
        });
      } else {
        // Create new config
        response = await fetch(`${BACKEND_API_URL}/llm/configs/create`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            ...configForm, 
            foundation_id: selectedFoundation?.id 
          })
        });
      }
      
      if (response.ok) {
        setShowConfigForm(false);
        setConfigForm({...defaultConfig, foundation_id: selectedFoundation?.id || 0});
        setIsEditing(false);
        if (selectedFoundation) {
          fetchConfigs(selectedFoundation.id);
        }
      }
    } catch (error) {
      console.error('Error submitting config:', error);
    }
  };

  // Delete foundation
  const handleDeleteFoundation = async (id: number) => {
    try {
      const response = await fetch(`${BACKEND_API_URL}/llm/foundations/delete/${id}`, { 
        method: 'DELETE' 
      });
      if (response.ok) {
        fetchFoundations();
        if (selectedFoundation?.id === id) {
          setSelectedFoundation(null);
          setConfigs([]);
        }
      }
    } catch (error) {
      console.error('Error deleting foundation:', error);
    }
  };

  // Delete config
  const handleDeleteConfig = async (id: number) => {
    try {
      const response = await fetch(`${BACKEND_API_URL}/llm/configs/delete/${id}`, { 
        method: 'DELETE' 
      });
      if (response.ok && selectedFoundation) {
        fetchConfigs(selectedFoundation.id);
      }
    } catch (error) {
      console.error('Error deleting config:', error);
    }
  };

  // Edit foundation
  const handleEditFoundation = (foundation: Foundation) => {
    setFoundationForm(foundation);
    setIsEditing(true);
    setFoundationFormTitle("Edit LLM Foundation");
    setShowFoundationForm(true);
  };

  // Edit config
  const handleEditConfig = (config: Config) => {
    setConfigForm(config);
    setIsEditing(true);
    setConfigFormTitle("Edit LLM Config");
    setShowConfigForm(true);
  };

  useEffect(() => {
    fetchFoundations();
  }, []);

  useEffect(() => {
    if (selectedFoundation) {
      fetchConfigs(selectedFoundation.id);
    }
  }, [selectedFoundation]);

  return (
    <div className="p-4 space-y-4">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">LLM Management</h1>
        <Dialog open={showFoundationForm} onOpenChange={(open) => {
          setShowFoundationForm(open);
          if (!open) setIsEditing(false);
        }}>
          <DialogTrigger asChild>
            <Button>Add Foundation</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{foundationFormTitle}</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <Select
                value={foundationForm.provider}
                onValueChange={(value) => setFoundationForm({ ...foundationForm, provider: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select Provider" />
                </SelectTrigger>
                <SelectContent>
                {Object.entries(ProviderTypeMap).map(([key, label]) => (
                 <SelectItem key={key} value={label}>
                  {key}
                  </SelectItem>
                ))}
                </SelectContent>
              </Select>
              <Input
                placeholder="Model ID"
                value={foundationForm.model_id}
                onChange={(e) => setFoundationForm({ ...foundationForm, model_id: e.target.value })}
              />
              <Input
                placeholder="Description"
                value={foundationForm.description}
                onChange={(e) => setFoundationForm({ ...foundationForm, description: e.target.value })}
              />
              {isEditing && (
                <div className="flex items-center space-x-2">
                  <label htmlFor="is-active">Active:</label>
                  <input
                    type="checkbox"
                    id="is-active"
                    checked={foundationForm.is_active}
                    onChange={(e) => setFoundationForm({ ...foundationForm, is_active: e.target.checked })}
                  />
                </div>
              )}
              <Button onClick={handleFoundationSubmit}>
                {isEditing ? 'Update Foundation' : 'Create Foundation'}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="md:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle>LLM Foundations</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {foundations.length === 0 && (
                  <div className="text-center text-gray-500 py-4">No foundations available</div>
                )}
                
                {foundations.map((foundation) => (
                  <div
                    key={foundation.id}
                    className={`p-2 border rounded ${
                      selectedFoundation?.id === foundation.id ? 'bg-blue-100 border-blue-300' : ''
                    }`}
                  >
                    <div className="flex justify-between items-center">
                      <div 
                        className="cursor-pointer flex-grow"
                        onClick={() => setSelectedFoundation(foundation)}
                      >
                        <div className="text-sm text-blue-600">Provider: {foundation.provider}</div>
                        <div className="text-sm text-gray-500">ID: {foundation.model_id}</div>
                      </div>
                      <div className="flex space-x-2">
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => handleEditFoundation(foundation)}
                        >
                          Edit
                        </Button>
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button variant="destructive" size="sm">Delete</Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>Delete Foundation</AlertDialogTitle>
                              <AlertDialogDescription>
                                Are you sure you want to delete this foundation? All associated configs will also be deleted. This action cannot be undone.
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>Cancel</AlertDialogCancel>
                              <AlertDialogAction onClick={() => handleDeleteFoundation(foundation.id)}>
                                Delete
                              </AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="md:col-span-2">
          {selectedFoundation ? (
            <Card>
              <CardHeader>
                <div className="flex justify-between items-center">
                  <CardTitle>Configs for {selectedFoundation.model_id}</CardTitle>
                  <Dialog open={showConfigForm} onOpenChange={(open) => {
                    setShowConfigForm(open);
                    if (!open) setIsEditing(false);
                  }}>
                    <DialogTrigger asChild>
                      <Button>Add Config</Button>
                    </DialogTrigger>
                    <DialogContent className="max-w-md">
                      <DialogHeader>
                        <DialogTitle>{configFormTitle}</DialogTitle>
                      </DialogHeader>
                      <div className="space-y-4 max-h-[70vh] overflow-y-auto">
                        <Input
                          placeholder="Name"
                          value={configForm.name}
                          onChange={(e) => setConfigForm({ ...configForm, name: e.target.value })}
                        />
                        <div>
                          <label className="text-sm font-medium">Temperature</label>
                          <Input
                            type="number"
                            min={0}
                            max={1}
                            step={0.1}
                            placeholder="Temperature"
                            value={configForm.temperature}
                            onChange={(e) => setConfigForm({ ...configForm, temperature: parseFloat(e.target.value) })}
                          />
                        </div>
                        <div>
                          <label className="text-sm font-medium">Max Tokens</label>
                          <Input
                            type="number"
                            placeholder="Max Tokens"
                            min={100}
                            step={100}
                            max={8000}
                            value={configForm.max_tokens}
                            onChange={(e) => setConfigForm({ ...configForm, max_tokens: parseInt(e.target.value) })}
                          />
                        </div>
                        <div>
                          <label className="text-sm font-medium">Top P</label>
                          <Input
                            type="number"
                            min={0}
                            max={1}
                            step={0.1}
                            placeholder="Top P"
                            value={configForm.top_p}
                            onChange={(e) => setConfigForm({ ...configForm, top_p: parseFloat(e.target.value) })}
                          />
                        </div>
                        <div>
                          <label className="text-sm font-medium">Frequency Penalty</label>
                          <Input
                            type="number"
                            min={0}
                            max={2}
                            step={0.1}
                            placeholder="Frequency Penalty"
                            value={configForm.frequency_penalty}
                            onChange={(e) => setConfigForm({ ...configForm, frequency_penalty: parseFloat(e.target.value) })}
                          />
                        </div>
                        <div>
                          <label className="text-sm font-medium">Presence Penalty</label>
                          <Input
                            type="number"
                            min={0}
                            max={2}
                            step={0.1}
                            placeholder="Presence Penalty"
                            value={configForm.presence_penalty}
                            onChange={(e) => setConfigForm({ ...configForm, presence_penalty: parseFloat(e.target.value) })}
                          />
                        </div>
                        <div>
                          <label className="text-sm font-medium">System Prompt</label>
                          <Textarea
                            placeholder="System Prompt"
                            rows={5}
                            value={configForm.system_prompt}
                            onChange={(e) => setConfigForm({ ...configForm, system_prompt: e.target.value })}
                          />
                        </div>
                        <Button onClick={handleConfigSubmit}>
                          {isEditing ? 'Update Config' : 'Create Config'}
                        </Button>
                      </div>
                    </DialogContent>
                  </Dialog>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {configs.length === 0 && (
                    <div className="text-center text-gray-500 py-4">No configs available for this foundation</div>
                  )}
                  
                  {configs.map((config) => (
                    <Card key={config.id}>
                      <CardContent className="p-4">
                        <div className="flex justify-between items-start">
                          <div className="flex-grow">
                            <h3 className="font-medium">{config.name}</h3>
                            <div className="text-sm text-gray-500 space-y-1">
                              <div>Temperature: {config.temperature} | Max Tokens: {config.max_tokens}</div>
                              <div>Top P: {config.top_p} | Frequency Penalty: {config.frequency_penalty} | Presence Penalty: {config.presence_penalty}</div>
                              <div className="mt-2">
                                <div className="text-sm font-medium">System Prompt:</div>
                                <div className="text-sm text-gray-600 p-2 bg-gray-50 rounded border max-h-24 overflow-y-auto">
                                  {config.system_prompt}
                                </div>
                              </div>
                            </div>
                          </div>
                          <div className="flex space-x-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleEditConfig(config)}
                            >
                              Edit
                            </Button>
                            <AlertDialog>
                              <AlertDialogTrigger asChild>
                                <Button variant="destructive" size="sm">Delete</Button>
                              </AlertDialogTrigger>
                              <AlertDialogContent>
                                <AlertDialogHeader>
                                  <AlertDialogTitle>Delete Config</AlertDialogTitle>
                                  <AlertDialogDescription>
                                    Are you sure you want to delete this config? This action cannot be undone.
                                  </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                                  <AlertDialogAction onClick={() => handleDeleteConfig(config.id)}>
                                    Delete
                                  </AlertDialogAction>
                                </AlertDialogFooter>
                              </AlertDialogContent>
                            </AlertDialog>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="p-8 text-center text-gray-500">
                Select a foundation to view its configurations
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};

export default LLMComponent;