'use client';

import React, { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Plus, Settings2, Trash2, Save, X, Database } from 'lucide-react';
import { toast } from '@/components/ui/use-toast';

const BACKEND_API_URL = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000';

type AgentType = 'react' | 'reflection';
const agentTypeMap: Record<AgentType, string> = {
  react: "React",
  reflection: "Reflection"
};
interface Foundation {
  id: number;
  provider: string;
  model_id: string;
  description?: string;
}

interface Config {
  id: number;
  foundation_id: number;
  name: string;
  temperature: number;
  max_tokens: number;
  system_prompt: string;
}

interface KnowledgeBase {
  id: number;
  name: string;
  description?: string;
  created_at: string;
  updated_at?: string;
  is_active: boolean;
}

interface Agent {
  id: number;
  name: string;
  agent_type: AgentType;
  foundation_id?: number;
  config_id?: number;
  description?: string;
  configuration: Record<string, any>;
  tools: string[];
  knowledge_bases?: KnowledgeBase[];
  created_at: string;
  updated_at?: string;
  is_active: boolean;
}

interface AgentFormData {
  name: string;
  agent_type: AgentType;
  foundation_id?: number;
  config_id?: number;
  description?: string;
  configuration: Record<string, any>;
  tools: string[];
  kb_ids: number[];
}

export default function AgentComponent() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [foundations, setFoundations] = useState<Foundation[]>([]);
  const [configs, setConfigs] = useState<Config[]>([]);
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [loading, setLoading] = useState(false);
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [toolInput, setToolInput] = useState('');
  const [selectedFoundationId, setSelectedFoundationId] = useState<number>();
  const [editingConfigs, setEditingConfigs] = useState<Config[]>([]);
  
  const initialFormData: AgentFormData = {
    name: '',
    agent_type: 'react',
    foundation_id: undefined,
    config_id: undefined,
    description: '',
    configuration: {},
    tools: [],
    kb_ids: [],
  };

  const [formData, setFormData] = useState<AgentFormData>(initialFormData);
  console.log(editingAgent)
  useEffect(() => {
    fetchAgents();
    fetchFoundations();
    fetchKnowledgeBases();
  }, []);

  useEffect(() => {
    if (editingAgent?.foundation_id) {
      fetchConfigsForFoundation(editingAgent.foundation_id)
        .then(configs => setEditingConfigs(configs));
    }
  }, [editingAgent?.foundation_id]);

  useEffect(() => {
    if (selectedFoundationId) {
      fetchConfigsForFoundation(selectedFoundationId);
    }
  }, [selectedFoundationId]);

  const fetchAgents = async () => {
    try {
      const response = await fetch(`${BACKEND_API_URL}/agent/get-all`);
      if (!response.ok) throw new Error('Failed to fetch agents');
      const data = await response.json();
      setAgents(data);
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to fetch agents",
        variant: "destructive",
      });
    }
  };

  const fetchFoundations = async () => {
    try {
      const response = await fetch(`${BACKEND_API_URL}/llm/foundations/get`);
      if (!response.ok) throw new Error('Failed to fetch foundations');
      const data = await response.json();
      setFoundations(data);
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to fetch foundations",
        variant: "destructive",
      });
    }
  };

  const fetchKnowledgeBases = async () => {
    try {
      const response = await fetch(`${BACKEND_API_URL}/kb/`);
      if (!response.ok) throw new Error('Failed to fetch knowledge bases');
      const data = await response.json();
      setKnowledgeBases(data);
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to fetch knowledge bases",
        variant: "destructive",
      });
    }
  };

  const fetchConfigsForFoundation = async (foundationId: number) => {
    try {
      const response = await fetch(`${BACKEND_API_URL}/llm/foundations/${foundationId}/configs`);
      if (!response.ok) throw new Error('Failed to fetch configs');
      const data = await response.json();
      setConfigs(data);
      return data;
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to fetch configs",
        variant: "destructive",
      });
    }
  };

  const handleCreateAgent = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await fetch(`${BACKEND_API_URL}/agent/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      
      if (!response.ok) throw new Error('Failed to create agent');
      
      await fetchAgents();
      setFormData(initialFormData);
      setSelectedFoundationId(undefined);
      toast({
        title: "Success",
        description: "Agent created successfully",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to create agent",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateAgent = async (agent: Agent) => {
    try {
      // Get selected KB IDs from editing agent
      const kbIds = agent.knowledge_bases?.map(kb => kb.id) || [];
      
      const response = await fetch(`${BACKEND_API_URL}/agent/update/${agent.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: agent.name,
          agent_type: agent.agent_type,
          foundation_id: agent.foundation_id,
          config_id: agent.config_id,
          description: agent.description,
          configuration: agent.configuration,
          tools: agent.tools,
          kb_ids: kbIds,
        }),
      });
      
      if (!response.ok) throw new Error('Failed to update agent');
      
      await fetchAgents();
      setIsEditDialogOpen(false);
      setEditingAgent(null);
      toast({
        title: "Success",
        description: "Agent updated successfully",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to update agent",
        variant: "destructive",
      });
    }
  };

  const handleFoundationChange = (foundationId: string) => {
    const numericId = parseInt(foundationId);
    setSelectedFoundationId(numericId);
    setFormData({
      ...formData,
      foundation_id: numericId,
      config_id: undefined,
    });
  };

  const getFoundationName = (foundationId?: number) => {
    if (!foundationId) return undefined;
    const foundation = foundations.find(f => f.id === foundationId);
    return foundation ? foundation.provider : undefined;
  };
  
  const getConfigName = (configId?: number) => {
    if (!configId) return undefined;
    const config = editingConfigs.find(c => c.id === configId);
    return config ? config.name : undefined;
  };

  const handleDeleteAgent = async (agentId: number) => {
    if (!confirm('Are you sure you want to delete this agent?')) return;
    
    try {
      const response = await fetch(`${BACKEND_API_URL}/agent/delete/${agentId}`, {
        method: 'DELETE',
      });
      
      if (!response.ok) throw new Error('Failed to delete agent');
      
      await fetchAgents();
      toast({
        title: "Success",
        description: "Agent deleted successfully",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to delete agent",
        variant: "destructive",
      });
    }
  };

  const handleAddTool = (isEditing: boolean) => {
    if (!toolInput.trim()) return;
    
    if (isEditing && editingAgent) {
      setEditingAgent({
        ...editingAgent,
        tools: [...editingAgent.tools, toolInput.trim()]
      });
    } else {
      setFormData({
        ...formData,
        tools: [...formData.tools, toolInput.trim()]
      });
    }
    setToolInput('');
  };

  const handleRemoveTool = (index: number, isEditing: boolean) => {
    if (isEditing && editingAgent) {
      const newTools = [...editingAgent.tools];
      newTools.splice(index, 1);
      setEditingAgent({
        ...editingAgent,
        tools: newTools
      });
    } else {
      const newTools = [...formData.tools];
      newTools.splice(index, 1);
      setFormData({
        ...formData,
        tools: newTools
      });
    }
  };

  const handleConfigChange = (configId: string) => {
    setFormData({
      ...formData,
      config_id: parseInt(configId),
    });
  };

  const handleKnowledgeBaseChange = (kbId: number) => {
    const currentKbIds = formData.kb_ids;
    
    // Toggle KB selection
    if (currentKbIds.includes(kbId)) {
      setFormData({
        ...formData,
        kb_ids: currentKbIds.filter(id => id !== kbId)
      });
    } else {
      setFormData({
        ...formData,
        kb_ids: [...currentKbIds, kbId]
      });
    }
  };

  const handleEditKnowledgeBaseChange = (kbId: number) => {
    if (!editingAgent) return;
    
    // Get current KBs
    const currentKBs = editingAgent.knowledge_bases || [];
    
    // Check if KB is already selected
    const isSelected = currentKBs.some(kb => kb.id === kbId);
    
    // Update editing agent's knowledge bases
    if (isSelected) {
      // Remove KB
      setEditingAgent({
        ...editingAgent,
        knowledge_bases: currentKBs.filter(kb => kb.id !== kbId)
      });
    } else {
      // Add KB
      const kbToAdd = knowledgeBases.find(kb => kb.id === kbId);
      if (kbToAdd) {
        setEditingAgent({
          ...editingAgent,
          knowledge_bases: [...currentKBs, kbToAdd]
        });
      }
    }
  };

  return (
    <div className="max-w-7xl mx-auto p-4">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="md:col-span-1 p-6">
          <h2 className="text-xl font-bold mb-4">Create New Agent</h2>
          <form onSubmit={handleCreateAgent} className="space-y-4">
            <Input
              placeholder="Agent Name"
              value={formData.name}
              onChange={(e) => setFormData({...formData, name: e.target.value})}
              required
            />
            
            <Select
              value={formData.agent_type}
              onValueChange={(value: AgentType) => 
                setFormData({...formData, agent_type: value})
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="Select agent type" />
              </SelectTrigger>
              <SelectContent>
              {Object.entries(agentTypeMap).map(([key, label]) => (
                <SelectItem key={key} value={key}>
                  {label}
                </SelectItem>
              ))}
              </SelectContent>
            </Select>

            <Select
              value={formData.foundation_id?.toString()}
              onValueChange={handleFoundationChange}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select foundation" />
              </SelectTrigger>
              <SelectContent>
                {foundations.map((foundation) => (
                  <SelectItem key={foundation.id} value={foundation.id.toString()}>
                    {foundation.provider}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {selectedFoundationId && (
              <Select
                value={formData.config_id?.toString()}
                onValueChange={handleConfigChange}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select config" />
                </SelectTrigger>
                <SelectContent>
                  {configs.map((config) => (
                    <SelectItem key={config.id} value={config.id.toString()}>
                      {config.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
            
            <Textarea
              placeholder="Description"
              value={formData.description}
              onChange={(e) => setFormData({...formData, description: e.target.value})}
            />

            {/* Knowledge Base Section - Sử dụng input checkbox thông thường */}
            <div className="space-y-2">
              <p className="text-sm font-medium">Knowledge Bases</p>
              <div className="border rounded-md p-3 max-h-40 overflow-y-auto space-y-2">
                {knowledgeBases.length > 0 ? (
                  knowledgeBases.map((kb) => (
                    <div key={kb.id} className="flex items-center space-x-2">
                      <input 
                        type="checkbox" 
                        id={`kb-${kb.id}`} 
                        checked={formData.kb_ids.includes(kb.id)}
                        onChange={() => handleKnowledgeBaseChange(kb.id)}
                        className="rounded border-gray-300"
                      />
                      <label 
                        htmlFor={`kb-${kb.id}`}
                        className="text-sm cursor-pointer"
                      >
                        {kb.name}
                      </label>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-gray-500">No knowledge bases available</p>
                )}
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex gap-2">
                <Input
                  placeholder="Add tool"
                  value={toolInput}
                  onChange={(e) => setToolInput(e.target.value)}
                />
                <Button 
                  type="button" 
                  variant="outline"
                  onClick={() => handleAddTool(false)}
                >
                  Add
                </Button>
              </div>
              <div className="flex flex-wrap gap-2">
                {formData.tools.map((tool, index) => (
                  <span
                    key={index}
                    className="bg-gray-100 rounded-full px-3 py-1 text-sm flex items-center gap-2"
                  >
                    {tool}
                    <button
                      type="button"
                      onClick={() => handleRemoveTool(index, false)}
                      className="text-red-500 hover:text-red-700"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
            </div>
            
            <Button type="submit" disabled={loading} className="w-full">
              <Plus className="w-4 h-4 mr-2" />
              Create Agent
            </Button>
          </form>
        </Card>

        <div className="md:col-span-2">
          <h2 className="text-2xl font-bold mb-4">Agents</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {agents.map((agent) => (
              <Card key={agent.id} className="p-4">
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="font-semibold">{agent.name}</h3>
                    <p className="text-sm text-gray-500">Type: <b>{agent.agent_type}</b></p>
                  </div>
                  <div className="flex gap-2">
                    <Dialog open={isEditDialogOpen && editingAgent?.id === agent.id}>
                      <DialogTrigger asChild>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            setEditingAgent(agent);
                            setIsEditDialogOpen(true);
                          }}
                        >
                          <Settings2 className="w-4 h-4" />
                        </Button>
                      </DialogTrigger>
                      <DialogContent className="max-w-lg">
                        <DialogHeader>
                          <DialogTitle>Edit Agent</DialogTitle>
                        </DialogHeader>
                        {editingAgent && (
                          <div className="space-y-4">
                            <Input
                              placeholder="Agent Name"
                              value={editingAgent.name}
                              onChange={(e) => setEditingAgent({
                                ...editingAgent,
                                name: e.target.value
                              })}
                            />
                            <Select
                              value={editingAgent.agent_type}
                              onValueChange={(value: AgentType) => 
                                setEditingAgent({
                                  ...editingAgent,
                                  agent_type: value
                                })
                              }
                            >
                              <SelectTrigger>
                              <SelectValue>
                                {editingAgent.agent_type === 'react' ? 'React' : 'Reflection'}
                              </SelectValue>
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="react">React</SelectItem>
                                <SelectItem value="reflection">Reflection</SelectItem>
                              </SelectContent>
                            </Select>
                            <Select
                              value={editingAgent.foundation_id?.toString()}
                              onValueChange={(e) => setEditingAgent({
                                ...editingAgent,
                                foundation_id: parseInt(e)
                              })}
                            >
                              <SelectTrigger>
                              <SelectValue>
                                {getFoundationName(editingAgent.foundation_id) || "Select foundation"}
                              </SelectValue>
                              </SelectTrigger>
                              <SelectContent>
                                {foundations.map((foundation) => (
                                  <SelectItem key={foundation.id} value={foundation.id.toString()}>
                                    {foundation.provider}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                            <Select
                              value={editingAgent.config_id?.toString()}
                              onValueChange={(e) => setEditingAgent({
                                ...editingAgent,
                                config_id: parseInt(e)
                              })}
                            >
                              <SelectTrigger>
                              <SelectValue>
                                {getConfigName(editingAgent.config_id) || "Select config"}
                              </SelectValue>
                              </SelectTrigger>
                              <SelectContent>
                                {configs.map((config) => (
                                  <SelectItem key={config.id} value={config.id.toString()}>
                                    {config.name}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                            
                            <Textarea
                              placeholder="Description"
                              value={editingAgent.description}
                              onChange={(e) => setEditingAgent({
                                ...editingAgent,
                                description: e.target.value
                              })}
                            />
                            
                            {/* Edit Knowledge Base Section - Sử dụng input checkbox thông thường */}
                            <div className="space-y-2">
                              <p className="text-sm font-medium">Knowledge Bases</p>
                              <div className="border rounded-md p-3 max-h-40 overflow-y-auto space-y-2">
                                {knowledgeBases.length > 0 ? (
                                  knowledgeBases.map((kb) => (
                                    <div key={kb.id} className="flex items-center space-x-2">
                                      <input 
                                        type="checkbox" 
                                        id={`edit-kb-${kb.id}`} 
                                        checked={editingAgent.knowledge_bases?.some(k => k.id === kb.id) || false}
                                        onChange={() => handleEditKnowledgeBaseChange(kb.id)}
                                        className="rounded border-gray-300"
                                      />
                                      <label 
                                        htmlFor={`edit-kb-${kb.id}`}
                                        className="text-sm cursor-pointer"
                                      >
                                        {kb.name}
                                      </label>
                                    </div>
                                  ))
                                ) : (
                                  <p className="text-sm text-gray-500">No knowledge bases available</p>
                                )}
                              </div>
                            </div>
                            
                            <div className="space-y-2">
                              <div className="flex gap-2">
                                <Input
                                  placeholder="Add tool"
                                  value={toolInput}
                                  onChange={(e) => setToolInput(e.target.value)}
                                />
                                <Button 
                                  type="button" 
                                  variant="outline"
                                  onClick={() => handleAddTool(true)}
                                >
                                  Add
                                </Button>
                              </div>
                              <div className="flex flex-wrap gap-2">
                                {editingAgent.tools.map((tool, index) => (
                                  <span
                                    key={index}
                                    className="bg-gray-100 rounded-full px-3 py-1 text-sm flex items-center gap-2"
                                  >
                                    {tool}
                                    <button
                                      type="button"
                                      onClick={() => handleRemoveTool(index, true)}
                                      className="text-red-500 hover:text-red-700"
                                    >
                                      <X className="w-3 h-3" />
                                    </button>
                                  </span>
                                ))}
                              </div>
                            </div>
                            <div className="flex justify-end gap-2">
                              <Button
                                variant="outline"
                                onClick={() => {
                                  setIsEditDialogOpen(false);
                                  setEditingAgent(null);
                                }}
                              >
                                Cancel
                              </Button>
                              <Button
                                onClick={() => handleUpdateAgent(editingAgent)}
                              >
                                <Save className="w-4 h-4 mr-2" />
                                Save Changes
                              </Button>
                            </div>
                          </div>
                        )}
                      </DialogContent>
                    </Dialog>
                    <Button 
                      variant="destructive" 
                      size="sm"
                      onClick={() => handleDeleteAgent(agent.id)}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
                <p className="text-sm mt-2">{agent.description}</p>
                
                {/* Display knowledge bases */}
                {agent.knowledge_bases && agent.knowledge_bases.length > 0 && (
                  <div className="mt-2">
                    <div className="flex items-center text-sm text-gray-600 mb-1">
                      <Database className="w-3 h-3 mr-1" />
                      <span>Knowledge Bases:</span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {agent.knowledge_bases.map((kb) => (
                        <span 
                          key={kb.id}
                          className="inline-block bg-blue-100 text-blue-800 rounded-full px-3 py-1 text-xs"
                        >
                          {kb.name}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* Display tools */}
                {agent.tools && agent.tools.length > 0 && (
                  <div className="mt-2">
                    <div className="flex flex-wrap gap-2">
                      {agent.tools.map((tool, index) => (
                        <span 
                          key={index}
                          className="inline-block bg-gray-100 rounded-full px-3 py-1 text-sm"
                        >
                          {tool}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </Card>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}